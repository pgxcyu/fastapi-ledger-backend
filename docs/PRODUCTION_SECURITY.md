# 生产环境安全配置建议

## 🔒 基础安全设置

### 1. 防火墙配置
```bash
# 启用ufw防火墙
sudo ufw enable

# 允许SSH
sudo ufw allow ssh

# 允许HTTP和HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 拒绝其他端口
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 查看状态
sudo ufw status
```

### 2. SSH安全
```bash
# 编辑SSH配置
sudo nano /etc/ssh/sshd_config

# 推荐配置：
Port 22                    # 可以改为其他端口
PermitRootLogin no        # 禁止root登录
PasswordAuthentication no # 仅允许密钥登录
PubkeyAuthentication yes  # 允许密钥登录
MaxAuthTries 3           # 最大尝试次数

# 重启SSH服务
sudo systemctl restart sshd
```

### 3. 系统更新
```bash
# 设置自动安全更新
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 手动更新系统
sudo apt update && sudo apt upgrade -y
```

## 🔐 应用安全配置

### 1. 环境变量安全
- ✅ SECRET_KEY: 使用强随机密钥（至少32字符）
- ✅ PG_PASSWORD: 使用强密码（包含大小写字母、数字、特殊字符）
- ✅ CORS_ALLOW_ORIGINS: 仅允许您的域名
- ✅ 数据库不暴露在公网（仅内网访问）

### 2. SSL/TLS配置
- ✅ 使用TLS 1.2和1.3
- ✅ 禁用弱加密算法
- ✅ 启用HSTS（HTTP严格传输安全）
- ✅ 定期更新证书

### 3. Nginx安全头
- ✅ X-Frame-Options: DENY
- ✅ X-Content-Type-Options: nosniff
- ✅ X-XSS-Protection: "1; mode=block"
- ✅ Strict-Transport-Security

## 📊 监控和日志

### 1. 日志管理
```bash
# 配置日志轮转
sudo nano /etc/logrotate.d/docker-compose

# 内容：
/var/log/docker/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /path/to/docker-compose.production.yml restart nginx
    endscript
}
```

### 2. 监控设置
- ✅ 使用Prometheus + Grafana监控
- ✅ 设置磁盘空间告警
- ✅ 监控服务健康状态
- ✅ 设置异常邮件通知

## 🔄 备份策略

### 1. 数据库备份
```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 数据库备份
docker-compose -f docker-compose.production.yml exec -T db pg_dump -U $PG_USER $PG_DB > $BACKUP_DIR/db_backup_$DATE.sql

# 文件备份
tar -czf $BACKUP_DIR/files_backup_$DATE.tar.gz static/ logs/

# 清理7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# 添加到crontab（每天凌晨2点备份）
echo "0 2 * * * /path/to/backup.sh" | crontab -
```

### 2. 应用备份
```bash
# 备份应用代码和配置
git archive --format=tar.gz --output=app_backup_$(date +%Y%m%d).tar.gz HEAD
```

## 🚨 故障排查

### 1. 常见问题
- **服务无法启动**: 检查端口占用、环境变量、磁盘空间
- **数据库连接失败**: 检查数据库服务状态、网络连接、认证信息
- **SSL证书问题**: 检查证书有效期、域名匹配、权限设置

### 2. 日志查看
```bash
# 查看所有服务日志
docker-compose -f docker-compose.production.yml logs

# 查看特定服务日志
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f worker

# 查看nginx访问日志
docker-compose -f docker-compose.production.yml exec nginx tail -f /var/log/nginx/access.log
```

## 📈 性能优化

### 1. 数据库优化
- 定期执行VACUUM和ANALYZE
- 监控慢查询
- 适当调整连接池大小

### 2. 应用优化
- 启用Gzip压缩
- 设置适当的缓存策略
- 优化静态文件服务

### 3. 系统优化
- 调整文件描述符限制
- 优化内核参数
- 监控资源使用情况

## 🔧 维护任务

### 1. 定期维护
- 每周：检查系统更新、清理日志
- 每月：更新Docker镜像、检查SSL证书
- 每季度：全面安全审计、性能评估

### 2. 紧急响应
- 建立故障响应流程
- 准备回滚方案
- 设置24/7监控告警