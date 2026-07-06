/**
 * 微博 Stealth 登录 — 自动保存 Cookie
 * 
 * 打开浏览器 → 用户手动扫码/输入登录 → 自动保存 Cookie
 * Cookie 保存到 ~/.local/china_cookies/weibo.json
 * 
 * 用法: node weibo_login.js
 */
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const COOKIE_DIR = path.join(os.homedir(), '.local', 'china_cookies');
const COOKIE_FILE = path.join(COOKIE_DIR, 'weibo.json');

fs.mkdirSync(COOKIE_DIR, { recursive: true });

(async () => {
  console.log('🚀 启动微博登录浏览器...\n');

  const userDataDir = path.join(os.homedir(), '.local/weibo-stealth-profile');
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1280,800',
      '--disable-dev-shm-usage',
      '--disable-default-apps',
      '--disable-extensions',
      '--disable-popup-blocking',
      '--password-store=basic',
    ],
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    locale: 'zh-CN',
  });

  const page = await context.newPage();

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
  });

  // 微博热搜页 — 未登录也能看到热搜，登录后 cookie 更稳定
  console.log('📱 正在打开微博热搜页...');
  await page.goto('https://weibo.com/newlogin?tabtype=weibo&gid=102803&url=https%3A%2F%2Fweibo.com', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await page.waitForTimeout(2000);

  console.log('✅ 浏览器已打开！');
  console.log('📋 请完成以下操作：');
  console.log('   1. 用手机微博 APP 扫码登录');
  console.log('   2. 或输入手机号+验证码登录');
  console.log('⏳ 等待登录... 成功后自动保存 Cookie\n');

  // 等待登录成功 — 检测页面上出现登录用户信息或跳转
  try {
    await page.waitForFunction(() => {
      return location.href.includes('weibo.com') && !location.href.includes('login');
    }, { timeout: 120000 });

    console.log('✅ 登录成功！保存 Cookie...');

    // 访问一次热搜 API 验证 cookie
    const cookies = await context.cookies();
    
    // 保存为标准 Playwright 格式
    fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
    console.log(`💾 Cookie 已保存到 ${COOKIE_FILE}`);
    console.log(`   共 ${cookies.length} 个 Cookie`);

    const keyKeys = ['SUB', 'SUBP', 'login_sid_t', 'XSRF-TOKEN'];
    const found = keyKeys.filter(k => cookies.some(c => c.name === k));
    console.log(`   关键 Cookie: ${found.join(', ')}`);
  } catch (e) {
    // 即使超时，也保存当前 cookie
    const cookies = await context.cookies();
    if (cookies.length > 5) {
      fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
      console.log(`\n💾 已保存 ${cookies.length} 个 Cookie (可能未完全登录)`);
    } else {
      console.log('\n⏱️ 超时，请确认已登录后重新运行');
    }
  }

  await context.close();
  console.log('👋 完成!');
})();
