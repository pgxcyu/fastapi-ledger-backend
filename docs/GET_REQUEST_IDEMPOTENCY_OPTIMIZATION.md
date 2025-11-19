# GET 请求幂等性优化建议

## 当前问题分析

### 1. GET 请求的特殊性
- **天然幂等**：HTTP 规范中 GET 请求应该是幂等的
- **安全操作**：不应修改服务器状态
- **可缓存性**：结果可以被缓存

### 2. 实际场景挑战
- **资源消耗**：数据库查询消耗资源
- **性能影响**：频繁重复请求影响性能
- **安全风险**：恶意重放可能导致 DDoS

## 优化方案

### 方案1：区分 GET 和其他请求的重放策略

```python
# 在 signing.py 中添加 GET 请求的特殊处理
async def verify_signature(
    request: Request,
    x_key_id: str = Header(..., alias="X-Key-Id"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    x_body_hash: str = Header('', alias="X-Body-Hash"),
    x_signature: str = Header(..., alias="X-Signature"),
    idem: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    # ... 前面的验证逻辑保持不变 ...
    
    # 2) 防重放：根据请求方法采用不同策略
    redis = getattr(request.app.state, "redis", None)
    if redis:
        method = request.method.upper()
        rkey = f"sig:{x_key_id}:{x_nonce}"
        
        if method == "GET":
            # GET 请求：更宽松的重放策略
            await _handle_get_replay_detection(redis, rkey, idem, x_nonce)
        else:
            # POST/PUT/DELETE：严格的重放策略
            await _handle_strict_replay_detection(redis, rkey, idem, x_nonce)

async def _handle_get_replay_detection(redis, rkey: str, idem: Optional[str], x_nonce: str):
    """处理 GET 请求的重放检测 - 更宽松的策略"""
    # 检查是否是重放请求
    if await redis.exists(rkey):
        if idem:
            # 有 Idempotency-Key：检查幂等键
            idem_key = f"idem:{idem}"
            if await redis.exists(idem_key):
                # 允许通过（可能是分页查询等）
                pass
            else:
                raise BizException(code=40101, message="重放检测")
        else:
            # 无 Idempotency-Key：检查时间差，但窗口更短
            first_request_time = await redis.get(rkey)
            if first_request_time:
                try:
                    first_time = int(first_request_time)
                    current_time = int(time.time())
                    time_diff = current_time - first_time
                    
                    # GET 请求只允许 5 秒内的重复（可能是网络重试）
                    if time_diff <= 5:
                        pass  # 允许通过
                    else:
                        raise BizException(code=40101, message="重放检测")
                except (ValueError, TypeError):
                    raise BizException(code=40101, message="重放检测")
            else:
                raise BizException(code=40101, message="重放检测")
    
    # 设置重放检测键，GET 请求过期时间更短
    await redis.setex(rkey, 60, str(int(time.time())))  # 1分钟过期
    
    # 如果提供了 Idempotency-Key，设置幂等键
    if idem:
        idem_key = f"idem:{idem}"
        await redis.setex(idem_key, 10, "1")  # 10秒过期

async def _handle_strict_replay_detection(redis, rkey: str, idem: Optional[str], x_nonce: str):
    """处理 POST/PUT/DELETE 请求的重放检测 - 严格策略"""
    # 检查是否是重放请求
    if await redis.exists(rkey):
        if idem:
            # 有 Idempotency-Key：检查幂等键
            idem_key = f"idem:{idem}"
            if await redis.exists(idem_key):
                pass  # 允许 token 刷新重试
            else:
                raise BizException(code=40101, message="重放检测")
        else:
            # 无 Idempotency-Key：30秒时间窗口
            first_request_time = await redis.get(rkey)
            if first_request_time:
                try:
                    first_time = int(first_request_time)
                    current_time = int(time.time())
                    time_diff = current_time - first_time
                    
                    if time_diff <= 30:
                        pass  # 允许 token 刷新重试
                    else:
                        raise BizException(code=40101, message="重放检测")
                except (ValueError, TypeError):
                    raise BizException(code=40101, message="重放检测")
            else:
                raise BizException(code=40101, message="重放检测")
    
    # 设置重放检测键，5分钟过期
    await redis.setex(rkey, 300, str(int(time.time())))
    
    # 如果提供了 Idempotency-Key，设置幂等键
    if idem:
        idem_key = f"idem:{idem}"
        await redis.setex(idem_key, 30, "1")
```

### 方案2：基于请求内容的缓存键

```python
# 为 GET 请求创建基于内容的缓存键
def _get_cache_key(request: Request, x_key_id: str) -> str:
    """为 GET 请求生成基于内容的缓存键"""
    method = request.method.upper()
    if method != "GET":
        return None
    
    # 包含路径、查询参数的规范化字符串
    path_only = request.url.path.rstrip('/')
    query_canon = canonicalize_query(request)
    content_hash = hashlib.sha256(f"{path_only}?{query_canon}".encode()).hexdigest()[:16]
    
    return f"get_cache:{x_key_id}:{content_hash}"

# 在路由中使用缓存
@router.get("/getRecords", response_model=R[PageResult[TransactionResponse]], 
           description="获取交易记录列表", 
           dependencies=[Depends(verify_signature), Depends(RateLimiter(times=10, seconds=60))])
async def get_transactions(
    request: Request,
    form: TransactionListQuery = Depends(), 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client),
):
    # 检查缓存
    cache_key = _get_cache_key(request, current_user.userid)
    if cache_key:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
    
    # 执行查询逻辑...
    result = R.ok(data=page)
    
    # 缓存结果（30秒）
    if cache_key:
        await redis_client.setex(cache_key, 30, result.json())
    
    return result
```

## 推荐策略

### 1. 分层处理策略

| 请求类型 | 重放检测策略 | 缓存策略 | 过期时间 |
|---------|-------------|----------|----------|
| GET | 宽松（5秒窗口） | 启用 | 1分钟 |
| POST | 严格（30秒窗口） | 不启用 | 5分钟 |
| PUT | 严格（30秒窗口） | 不启用 | 5分钟 |
| DELETE | 严格（30秒窗口） | 不启用 | 5分钟 |

### 2. 实施建议

```python
# 简化版本：直接在现有逻辑中添加 GET 判断
if await redis.exists(rkey):
    if request.method.upper() == "GET":
        # GET 请求：更宽松的策略
        if idem:
            idem_key = f"idem:{idem}"
            if await redis.exists(idem_key):
                pass
            else:
                raise BizException(code=40101, message="重放检测")
        else:
            # GET 请求：5秒时间窗口
            first_time = int(await redis.get(rkey) or 0)
            if int(time.time()) - first_time <= 5:
                pass
            else:
                raise BizException(code=40101, message="重放检测")
    else:
        # 其他请求：30秒时间窗口
        # ... 现有逻辑 ...

# 设置不同的过期时间
expiry = 60 if request.method.upper() == "GET" else 300
await redis.setex(rkey, expiry, str(int(time.time())))
```

## 总结

**GET 请求确实需要考虑幂等性，但可以采用更宽松的策略**：

1. **安全防护**：仍然需要防止恶意重放攻击
2. **性能优化**：可以使用缓存减少数据库查询
3. **用户体验**：允许短时间内的重复请求（网络重试等）
4. **资源控制**：设置更短的过期时间

这样既保证了安全性，又提升了用户体验和系统性能。