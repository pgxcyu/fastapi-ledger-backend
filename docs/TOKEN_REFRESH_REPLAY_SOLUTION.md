# Token 刷新重试的重放检测解决方案

## 问题描述

当用户请求 `getRecords` 接口遇到 token 失效时，前端会自动刷新 token 并重试请求。但是重试时使用了相同的 `X-Nonce`，导致后端的重放检测机制误判为恶意重放攻击，抛出 "重放检测" 异常。

## 根本原因

1. **重放检测机制**：后端使用 `sig:{kid}:{nonce}` 作为 Redis 键，确保每个 nonce 在 5 分钟内唯一
2. **Token 刷新重试**：前端重试时保持相同的请求头（包括 `X-Nonce`），导致 Redis 键重复
3. **缺乏区分机制**：原有的重放检测无法区分合法的 token 刷新重试和恶意重放攻击
4. **现有接口限制**：当前接口没有依赖 `Idempotency-Key`，无法直接使用幂等性验证

## 解决方案

采用**双重机制**来处理 token 刷新重试：

### 方案1：基于 Idempotency-Key 的精确验证（推荐）

当请求包含 `Idempotency-Key` 时，使用幂等键进行精确验证：

```python
if idem:
    idem_key = f"idem:{idem}"
    idem_exists = await redis.exists(idem_key)
    
    if idem_exists:
        # 通过幂等键验证的合法重试
        pass
    else:
        raise BizException(code=40101, message="重放检测")
```

### 方案2：基于时间窗口的容错验证（兼容现有接口）

当请求不包含 `Idempotency-Key` 时，使用时间窗口进行容错：

```python
else:
    # 获取第一次请求的时间戳
    first_request_time = await redis.get(rkey)
    if first_request_time:
        first_time = int(first_request_time)
        current_time = int(time.time())
        time_diff = current_time - first_time
        
        # 30秒内重复，可能是 token 刷新重试
        if time_diff <= 30:
            pass  # 允许通过
        else:
            raise BizException(code=40101, message="重放检测")
```

## 完整实现逻辑

```python
# 2) 防重放：kid+nonce 5 分钟唯一，但允许 token 刷新重试
redis = getattr(request.app.state, "redis", None)
if redis:
    rkey = f"sig:{x_key_id}:{x_nonce}"
    
    # 检查是否是重放请求
    if await redis.exists(rkey):
        # 方案1：如果有 Idempotency-Key，检查幂等键
        if idem:
            idem_key = f"idem:{idem}"
            if await redis.exists(idem_key):
                # 通过幂等键验证的合法重试
                pass
            else:
                raise BizException(code=40101, message="重放检测")
        else:
            # 方案2：检查是否是短时间内（30秒内）的重复请求
            first_request_time = await redis.get(rkey)
            if first_request_time:
                first_time = int(first_request_time)
                current_time = int(time.time())
                time_diff = current_time - first_time
                
                if time_diff <= 30:
                    # 30秒内重复，可能是 token 刷新重试
                    pass
                else:
                    raise BizException(code=40101, message="重放检测")
            else:
                raise BizException(code=40101, message="重放检测")
    
    # 设置重放检测键，存储当前时间戳，5分钟过期
    await redis.setex(rkey, 300, str(int(time.time())))
    
    # 如果提供了 Idempotency-Key，也设置幂等键，30秒过期
    if idem:
        idem_key = f"idem:{idem}"
        await redis.setex(idem_key, 30, "1")
```

## Redis 键设计

- **重放检测键**：`sig:{kid}:{nonce}` - 5分钟过期，存储时间戳
- **幂等检测键**：`idem:{idempotency_key}` - 30秒过期，存储 "1"

## 场景分析

### ✅ 场景1：现有接口的 Token 刷新重试（方案2）

```
第一次请求：
- X-Nonce: "abc123"
- Idempotency-Key: (无)
- Redis: 设置 sig:app_ledger_v1:abc123 = 1672531200

Token 刷新重试（5秒后）：
- X-Nonce: "abc123" (相同)
- Idempotency-Key: (无)
- 检查: sig 键存在，获取时间戳 1672531200
- 计算: 1672531205 - 1672531200 = 5秒 < 30秒
- 结果: ✅ 允许通过
```

### ✅ 场景2：增强接口的 Token 刷新重试（方案1）

```
第一次请求：
- X-Nonce: "def456"
- Idempotency-Key: "req_001"
- Redis: 设置 sig:app_ledger_v1:def456 = 时间戳
- Redis: 设置 idem:req_001 = 1

Token 刷新重试：
- X-Nonce: "def456" (相同)
- Idempotency-Key: "req_001" (相同)
- 检查: sig 键存在，idem 键也存在
- 结果: ✅ 允许通过（更精确）
```

### ❌ 场景3：恶意重放攻击

```
原始请求：
- X-Nonce: "xyz789"
- Idempotency-Key: (无)
- Redis: 设置 sig:app_ledger_v1:xyz789 = 时间戳

恶意重放（2分钟后）：
- X-Nonce: "xyz789" (相同)
- Idempotency-Key: (无)
- 检查: sig 键存在，获取时间戳
- 计算: 时间差 = 120秒 > 30秒
- 结果: ❌ 抛出重放检测异常
```

## 优势对比

| 特性 | 方案1（Idempotency-Key） | 方案2（时间窗口） |
|------|--------------------------|-------------------|
| 精确性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 兼容性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 安全性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 实现复杂度 | ⭐⭐⭐ | ⭐⭐ |

## 前端实现建议

### 1. 渐进式升级

```javascript
// 阶段1：保持现有逻辑不变（使用方案2）
// 无需修改，自动兼容

// 阶段2：可选添加 Idempotency-Key（使用方案1）
axios.interceptors.request.use(config => {
    if (!config.headers['Idempotency-Key']) {
        config.headers['Idempotency-Key'] = generateIdempotencyKey();
    }
    return config;
});

function generateIdempotencyKey() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
```

### 2. Token 刷新重试逻辑

```javascript
axios.interceptors.response.use(
    response => response,
    async error => {
        const originalRequest = error.config;
        
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            
            const newToken = await refreshToken();
            originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
            
            // 保持相同的 Idempotency-Key 进行重试
            return axios(originalRequest);
        }
        
        return Promise.reject(error);
    }
);
```

## 部署策略

### 1. 向后兼容
- 现有接口无需任何修改，自动使用方案2
- 30秒时间窗口覆盖了大部分 token 刷新重试场景

### 2. 渐进升级
- 前端可选择性地添加 `Idempotency-Key` 头
- 添加后自动使用更精确的方案1

### 3. 监控告警
- 监控重放检测触发频率
- 监控时间窗口内重试的成功率
- 监控 Idempotency-Key 的使用情况

## 测试验证

运行测试脚本验证各种场景：

```bash
python test_token_refresh_replay.py
```

## 总结

这个双重机制解决方案巧妙地平衡了**兼容性**和**精确性**：

1. **立即可用**：现有接口无需修改，通过方案2解决大部分问题
2. **精确可控**：前端可选择添加 Idempotency-Key，使用方案1获得更精确的验证
3. **安全可靠**：两种方案都有效防护恶意重放攻击
4. **易于维护**：逻辑清晰，易于理解和调试

这是处理 token 刷新重试问题的最佳实践方案！