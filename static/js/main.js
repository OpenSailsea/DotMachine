// 进度条颜色设置
document.addEventListener('DOMContentLoaded', function() {
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        const percentage = parseFloat(progressBar.style.width);
        if (percentage >= 90) {
            progressBar.style.setProperty('--progress-color', '#dc3545'); // 红色
        } else if (percentage >= 70) {
            progressBar.style.setProperty('--progress-color', '#ffc107'); // 黄色
        }
    }
});

// 确认操作
function confirmAction(message) {
    return confirm(message);
}

function toggleSidebar() {
    const sidebar = document.getElementById('mobile-sidebar');
    sidebar.classList.toggle('hidden');
}

// 添加平滑滚动
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
            // 在移动端点击导航后关闭侧边栏
            const sidebar = document.getElementById('mobile-sidebar');
            if (!sidebar.classList.contains('hidden')) {
                toggleSidebar();
            }
        }
    });
});

// 添加页面加载动画
document.addEventListener('DOMContentLoaded', function() {
    document.body.classList.add('loaded');
});

// 表单验证
document.addEventListener('DOMContentLoaded', function() {
    // 域名验证
    const domainForms = document.querySelectorAll('.add-website-form');
    domainForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const domainInput = form.querySelector('input[name="domain"]');
            const domain = domainInput.value;
            const pattern = /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$/;
            
            if (!pattern.test(domain)) {
                e.preventDefault();
                alert('请输入有效的域名，如example.com或sub.example.com');
            }
        });
    });
    
    // 端口验证
    const portForms = document.querySelectorAll('.add-port-form');
    portForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const portInput = form.querySelector('input[name="port"]');
            const port = parseInt(portInput.value);
            
            if (isNaN(port) || port < 1 || port > 65535) {
                e.preventDefault();
                alert('请输入有效的端口号（1-65535）');
            }
        });
    });
});

// 状态指示器更新
function updateStatusDots() {
    const dots = document.querySelectorAll('.status-dot');
    dots.forEach(dot => {
        // 这里可以添加实际的状态检查逻辑
        const status = dot.dataset.status;
        if (status === 'running') {
            dot.style.backgroundColor = '#28a745';
        } else if (status === 'stopped') {
            dot.style.backgroundColor = '#dc3545';
        } else {
            dot.style.backgroundColor = '#ffc107';
        }
    });
}

// 自动更新剩余天数显示
function updateExpiryDisplay() {
    const expiryBoxes = document.querySelectorAll('.expiry-box');
    expiryBoxes.forEach(box => {
        const days = parseInt(box.dataset.days);
        if (days <= 1) {
            box.classList.add('danger');
        } else if (days <= 5) {
            box.classList.add('warning');
        } else {
            box.classList.add('success');
        }
    });
}

// 防火墙规则表单处理
document.addEventListener('DOMContentLoaded', function() {
    const policyForm = document.querySelector('.policy-form');
    if (policyForm) {
        policyForm.addEventListener('submit', function(e) {
            const inputPolicy = policyForm.querySelector('select[name="input_policy"]').value;
            const outputPolicy = policyForm.querySelector('select[name="output_policy"]').value;
            
            if (inputPolicy === 'DROP' && outputPolicy === 'DROP') {
                if (!confirm('警告：设置入站和出站策略都为DROP可能导致无法访问服务器，是否继续？')) {
                    e.preventDefault();
                }
            }
        });
    }
});

// 复制功能
function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        alert('复制成功！');
    } catch (err) {
        alert('复制失败，请手动复制');
    }
    document.body.removeChild(textarea);
}

// 添加复制按钮到所有需要复制的元素
document.addEventListener('DOMContentLoaded', function() {
    const copyElements = document.querySelectorAll('[data-copy]');
    copyElements.forEach(element => {
        const copyButton = document.createElement('button');
        copyButton.className = 'button';
        copyButton.textContent = '复制';
        copyButton.onclick = function() {
            copyToClipboard(element.dataset.copy);
        };
        element.appendChild(copyButton);
    });
});

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    updateStatusDots();
    updateExpiryDisplay();
});
