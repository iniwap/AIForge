// 全局变量  
let matrixCanvas, matrixCtx;
let particles = [];
let demoCommands = [
    "分析全球股市趋势并生成投资建议",
    "创建一个智能聊天机器人",
    "处理Excel文件并生成可视化图表",
    "监控服务器状态并自动报警",
    "生成产品营销文案"
];
let currentCommandIndex = 0;

// 页面加载完成后初始化  
document.addEventListener('DOMContentLoaded', function () {
    initMatrixBackground();
    initTerminalDemo();
    initScrollAnimations();
    initInteractiveElements();
});

// 初始化矩阵背景  
function initMatrixBackground() {
    matrixCanvas = document.getElementById('matrix-canvas');
    matrixCtx = matrixCanvas.getContext('2d');

    resizeCanvas();
    createParticles();
    animateMatrix();

    window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
    matrixCanvas.width = window.innerWidth;
    matrixCanvas.height = window.innerHeight;
}

function createParticles() {
    particles = [];
    const particleCount = Math.floor((window.innerWidth * window.innerHeight) / 15000);

    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            size: Math.random() * 2 + 1,
            opacity: Math.random() * 0.5 + 0.2,
            color: `hsl(${180 + Math.random() * 60}, 100%, 70%)`
        });
    }
}

function animateMatrix() {
    matrixCtx.fillStyle = 'rgba(10, 10, 10, 0.05)';
    matrixCtx.fillRect(0, 0, matrixCanvas.width, matrixCanvas.height);

    particles.forEach(particle => {
        // 更新位置  
        particle.x += particle.vx;
        particle.y += particle.vy;

        // 边界检测  
        if (particle.x < 0 || particle.x > matrixCanvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > matrixCanvas.height) particle.vy *= -1;

        // 绘制粒子  
        matrixCtx.beginPath();
        matrixCtx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        matrixCtx.fillStyle = particle.color;
        matrixCtx.globalAlpha = particle.opacity;
        matrixCtx.fill();

        // 连接线  
        particles.forEach(otherParticle => {
            const distance = Math.sqrt(
                Math.pow(particle.x - otherParticle.x, 2) +
                Math.pow(particle.y - otherParticle.y, 2)
            );

            if (distance < 100) {
                matrixCtx.beginPath();
                matrixCtx.moveTo(particle.x, particle.y);
                matrixCtx.lineTo(otherParticle.x, otherParticle.y);
                matrixCtx.strokeStyle = `rgba(0, 255, 255, ${0.1 * (1 - distance / 100)})`;
                matrixCtx.lineWidth = 0.5;
                matrixCtx.stroke();
            }
        });
    });

    matrixCtx.globalAlpha = 1;
    requestAnimationFrame(animateMatrix);
}

// 初始化终端演示  
function initTerminalDemo() {
    const cursor = document.getElementById('demo-cursor');
    const commandText = document.getElementById('demo-command');
    const outputArea = document.getElementById('demo-output');

    if (!cursor || !commandText || !outputArea) return;

    // 光标闪烁  
    setInterval(() => {
        cursor.style.opacity = cursor.style.opacity === '0' ? '1' : '0';
    }, 500);

    // 开始演示  
    setTimeout(() => {
        startTypingDemo();
    }, 2000);
}

function startTypingDemo() {
    const commandText = document.getElementById('demo-command');
    const outputArea = document.getElementById('demo-output');

    if (!commandText || !outputArea) return;

    const command = demoCommands[currentCommandIndex];
    let charIndex = 0;

    // 清空之前的内容  
    commandText.textContent = '';
    outputArea.innerHTML = '';

    // 打字效果  
    const typingInterval = setInterval(() => {
        if (charIndex < command.length) {
            commandText.textContent += command[charIndex];
            charIndex++;
        } else {
            clearInterval(typingInterval);

            // 显示执行结果  
            setTimeout(() => {
                showDemoResult();
            }, 1000);
        }
    }, 100);
}

function showDemoResult() {
    const outputArea = document.getElementById('demo-output');
    if (!outputArea) return;

    const results = [
        '✅ 任务解析完成\\n🧠 调用认知引擎\\n⚡ 代码生成中...\\n🎯 执行成功',
        '✅ 智能分析完成\\n📊 数据处理中...\\n🔮 预测模型构建\\n🚀 结果已生成',
        '✅ 文件处理完成\\n📈 图表生成中...\\n🎨 可视化渲染\\n💎 输出完成',
        '✅ 监控系统启动\\n🔍 状态检测中...\\n⚠️ 异常预警设置\\n🛡️ 防护就绪',
        '✅ 内容分析完成\\n✍️ 文案生成中...\\n🎭 创意优化\\n📝 输出完成'
    ];

    const result = results[currentCommandIndex];
    const lines = result.split('\\n');
    let lineIndex = 0;

    const showLine = () => {
        if (lineIndex < lines.length) {
            const line = document.createElement('div');
            line.textContent = lines[lineIndex];
            line.style.color = '#00ff88';
            line.style.marginBottom = '0.5rem';
            outputArea.appendChild(line);
            lineIndex++;
            setTimeout(showLine, 800);
        } else {
            // 切换到下一个命令  
            currentCommandIndex = (currentCommandIndex + 1) % demoCommands.length;
            setTimeout(startTypingDemo, 3000);
        }
    };

    showLine();
}
// 初始化滚动动画  
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // 观察所有需要动画的元素  
    const animateElements = document.querySelectorAll(
        '.capability-node, .scenario-card, .metric-card, .arch-layer'
    );

    animateElements.forEach(el => {
        observer.observe(el);
    });
}

// 初始化交互元素  
function initInteractiveElements() {
    // 能力节点悬停效果  
    const capabilityNodes = document.querySelectorAll('.capability-node');
    capabilityNodes.forEach(node => {
        node.addEventListener('mouseenter', () => {
            node.style.transform = 'translateY(-10px) scale(1.02)';
        });

        node.addEventListener('mouseleave', () => {
            node.style.transform = 'translateY(0) scale(1)';
        });
    });

    // 架构层连接线动画  
    const archLayers = document.querySelectorAll('.arch-layer');
    archLayers.forEach((layer, index) => {
        if (index < archLayers.length - 1) {
            const connection = layer.querySelector('.layer-connections');
            if (connection) {
                connection.innerHTML = '<div class="connection-line"></div>';
            }
        }
    });
}

// 按钮交互函数  
function initializeDemo() {
    const demoSection = document.getElementById('capabilities');
    if (demoSection) {
        demoSection.scrollIntoView({ behavior: 'smooth' });
    }

    // 添加启动效果  
    const btn = event.target.closest('.btn-primary');
    if (btn) {
        btn.style.transform = 'scale(0.95)';
        setTimeout(() => {
            btn.style.transform = 'scale(1)';
        }, 150);
    }
}

function exploreCapabilities() {
    const capabilitiesSection = document.getElementById('capabilities');
    if (capabilitiesSection) {
        capabilitiesSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// 复制到剪贴板功能  
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target.closest('.copy-btn');
        if (btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="copy-icon">✅</span>';
            btn.style.background = '#00ff88';

            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.style.background = '';
            }, 2000);
        }
    }).catch(err => {
        console.error('复制失败:', err);
    });
}

// 添加 CSS 动画类  
const additionalCSS = `  
.animate-in {  
    animation: slideInUp 0.8s ease-out forwards;  
}  
  
@keyframes slideInUp {  
    from {  
        opacity: 0;  
        transform: translateY(30px);  
    }  
    to {  
        opacity: 1;  
        transform: translateY(0);  
    }  
}  
  
.connection-line {  
    width: 2px;  
    height: 30px;  
    background: linear-gradient(to bottom, var(--primary-color), transparent);  
    margin: 1rem auto;  
    position: relative;  
}  
  
.connection-line::after {  
    content: '';  
    position: absolute;  
    bottom: -5px;  
    left: 50%;  
    transform: translateX(-50%);  
    width: 0;  
    height: 0;  
    border-left: 5px solid transparent;  
    border-right: 5px solid transparent;  
    border-top: 8px solid var(--primary-color);  
}  
  
/* 添加更多动画效果 */  
.capability-node, .scenario-card, .metric-card {  
    opacity: 0;  
    transform: translateY(30px);  
    transition: all 0.6s ease-out;  
}  
  
.capability-node.animate-in,   
.scenario-card.animate-in,   
.metric-card.animate-in {  
    opacity: 1;  
    transform: translateY(0);  
}  
`;

// 动态添加 CSS  
const style = document.createElement('style');
style.textContent = additionalCSS;
document.head.appendChild(style);