/**
 * 小红书 stealth 登录 — 绕过 Playwright 自动化检测
 * 
 * 将 Playwright 的 Chromium 伪装成正常浏览器，绕过小红书反爬检测。
 * 运行后手动完成登录，Cookie 自动保存到 ~/.mcp/rednote/cookies.json
 * 
 * 用法: LD_LIBRARY_PATH="$HOME/.local/playwright-libs" node login_stealth.js
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const os = require('os');

const COOKIE_DIR = path.join(os.homedir(), '.mcp', 'rednote');
const COOKIE_FILE = path.join(COOKIE_DIR, 'cookies.json');

fs.mkdirSync(COOKIE_DIR, { recursive: true });

(async () => {
  console.log('🚀 启动 Stealth 浏览器...\n');

  const userDataDir = path.join(os.homedir(), '.local/xhs-stealth-profile');
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: [
      // 核心反检测参数
      '--disable-blink-features=AutomationControlled',
      '--disable-features=IsolateOrigins,site-per-process',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-web-security',
      '--disable-features=BlockInsecurePrivateNetworkRequests',
      // 模拟真实浏览器
      '--window-size=1280,800',
      '--disable-dev-shm-usage',
      // 禁用 automation 扩展
      '--disable-component-update',
      '--disable-default-apps',
      '--disable-extensions',
      '--disable-popup-blocking',
      '--password-store=basic',
      '--use-mock-keychain',
    ],
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    geolocation: { latitude: 31.2304, longitude: 121.4737 },
    permissions: ['geolocation'],
  });

  const page = await context.newPage();

  // 核心: 注入 JS 隐藏 webdriver 标记
  await page.addInitScript(() => {
    // 移除 webdriver 属性
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    // 伪造 chrome 对象
    window.chrome = { runtime: {} };
    // 伪造权限查询
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
      parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
    );
    // 覆盖 plugins 使其看起来像正常浏览器
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5],
    });
    // 伪造 languages
    Object.defineProperty(navigator, 'languages', {
      get: () => ['zh-CN', 'zh', 'en'],
    });
  });

  console.log('📱 正在打开小红书...');
  await page.goto('https://www.xiaohongshu.com/explore', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });

  // 等待用户操作
  console.log('✅ 浏览器已打开！');
  console.log('📋 请在浏览器窗口中完成以下操作之一：');
  console.log('   1. 如果显示登录页，用手机 APP 扫码登录');
  console.log('   2. 如果已登录，直接等待 Cookie 保存');
  console.log('');
  console.log('⏳ 等待登录... 成功登录后会自动保存 Cookie 并退出.\n');

  // 等待登录成功 — 检测侧边栏出现"我"字样
  try {
    await page.waitForFunction(() => {
      const channel = document.querySelector('.user.side-bar-component .channel');
      return channel && channel.textContent.trim() === '我';
    }, { timeout: 120000 }); // 给 2 分钟时间

    console.log('✅ 登录成功！保存 Cookie...');
    const cookies = await context.cookies();
    fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
    console.log(`💾 Cookie 已保存到 ${COOKIE_FILE}`);
    console.log(`   共 ${cookies.length} 个 Cookie`);

    // 验证 Cookie 关键字段
    const keyKeys = ['a1', 'web_session', 'websectiga', 'acw_tc'];
    const found = keyKeys.filter(k => cookies.some(c => c.name === k));
    console.log(`   关键 Cookie: ${found.join(', ')}`);
    if (found.length < 3) {
      console.log('   ⚠️ 缺少部分关键 Cookie，可能需要更完整的登录');
    }
  } catch (e) {
    console.log('\n⏱️ 超时未检测到登录，请确认已成功登录');
    console.log('   你可以手动在浏览器中登录后，再重新运行此脚本');
  }

  await context.close();
  console.log('\n👋 完成!');
})();
