# Git推送故障排除指南

## 问题分析

根据测试，我们发现：
- 网络连接到GitHub是正常的（ping测试成功）
- 可能存在HTTP推送的连接超时问题
- SSH连接需要主机密钥验证

## 解决方案

### 方案1：配置无需交互的SSH连接

```powershell
# 创建SSH配置目录
mkdir -p ~/.ssh

# 创建SSH配置文件，禁用主机密钥验证（仅临时使用）
@"
Host github.com
  StrictHostKeyChecking no
  UserKnownHostsFile=/dev/null
"@ | Out-File -FilePath ~/.ssh/config -Encoding utf8

# 生成SSH密钥（如果没有）
if (!(Test-Path ~/.ssh/id_ed25519)) {
    ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_ed25519 -N "" -q
}

# 显示公钥内容（需要复制到GitHub）
echo "请将以下公钥添加到GitHub:"
Get-Content ~/.ssh/id_ed25519.pub
```

### 方案2：优化HTTP推送配置

```powershell
# 增加缓冲区大小
git config --global http.postBuffer 524288000

# 设置较长的超时时间
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999

# 临时禁用SSL验证（仅临时使用）
git config --global http.sslVerify false

# 设置代理（如果需要）
# git config --global http.proxy http://代理地址:端口
```

### 方案3：使用Git凭证管理器

```powershell
# 下载并安装Git凭证管理器（GCM）
Invoke-WebRequest -Uri "https://github.com/git-ecosystem/git-credential-manager/releases/latest/download/gcmw-win-x86-64.msi" -OutFile "gcmw-win-x86-64.msi"
msiexec /i gcmw-win-x86-64.msi /qn

# 配置Git使用凭证管理器
git config --global credential.helper manager
```

### 方案4：使用HTTPS令牌认证

```powershell
# 生成GitHub个人访问令牌：https://github.com/settings/tokens
# 然后使用令牌进行推送
# git remote set-url origin https://用户名:令牌@github.com/用户名/仓库名.git
```

## 一键解决方案

以下是一个综合的一键解决脚本：

```powershell
# 优化Git配置
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999
git config --global http.sslVerify false

# 尝试使用不同的远程URL格式（替换为实际的用户名和仓库名）
$username = "你的GitHub用户名"
$repo = "你的仓库名"

# 创建备份
git remote rename origin origin_backup -f 2>$null

# 设置新的HTTPS远程（使用GitHub CLI格式）
git remote add origin https://github.com/$username/$repo.git

# 尝试推送
echo "正在尝试推送..."
git push origin master --no-verify
```

## 替代方案：使用GitHub Desktop

如果命令行持续遇到问题，可以尝试使用GitHub Desktop：

1. 下载并安装：https://desktop.github.com/
2. 克隆你的仓库
3. 进行更改并提交
4. 点击推送按钮

## 常见问题解答

1. **为什么会出现连接超时？**
   - 可能是网络限制、防火墙问题或GitHub服务器暂时不可用
   - 通常通过增加超时设置或使用SSH可以解决

2. **为什么SSH连接失败？**
   - 需要将SSH公钥添加到GitHub账户
   - 需要确认主机密钥（可以通过配置文件自动接受）

3. **如何检查我的更改是否成功？**
   - 使用`git status`查看本地状态
   - 使用`git log -n 5`查看最近的提交

4. **遇到其他问题怎么办？**
   - 检查GitHub状态页：https://www.githubstatus.com/
   - 尝试重启计算机或切换网络
   - 考虑使用VPN（如果在公司网络中）

希望这些解决方案能帮助你解决Git推送问题！