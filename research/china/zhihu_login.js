/**
 * 知乎 Stealth 登录 — 自动保存 Cookie
 * 
 * 打开浏览器 → 用户手动扫码/输入登录 → 自动保存 Cookie
 * Cookie 保存到 ~/.local/china_cookies/zhihu.json
 * 
 * 用法: node zhihu_login.js
 */
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const COOKIE_DIR = path.join(os.homedir(), '.local', 'china_cookies');
const COOKIE_FILE = path.join(COOKIE_DIR, 'zhihu.json');

fs.mkdirSync(COOKIE_DIR, { recursive: true });

(async () => {
  console.log('🚀 启动知乎登录浏览器...\n');

  const userDataDir = path.join(os.homedir(), '.local/zhihu-stealth-profile');
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

  console.log('📱 正在打开知乎热榜页...');
  await page.goto('https://www.zhihu.com/signin', {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await page.waitForTimeout(3000);

  console.log('✅ 浏览器已打开！');
  console.log('📋 请完成以下操作：');
  console.log('   1. 用手机知乎 APP 扫码登录');
  console.log('   2. 或输入手机号+验证码/密码登录');
  console.log('⏳ 等待登录... 成功后自动保存 Cookie\n');

  // 等待登录成功 — 页面跳转离开 signin
  try {
    await page.waitForFunction(() => {
      return location.href.includes('zhihu.com') && !location.href.includes('signin');
    }, { timeout: 180000 });

    // 等一会儿让页面完全加载
    await page.waitForTimeout(3000);
    
    console.log('✅ 检测到登录成功！');
    
    // 访问热榜页确认cookie有效
    console.log('📊 验证热榜页...');
    await page.goto('https://www.zhihu.com/hot');
    await page.waitForTimeout(3000);
    
    // 检查是否有热榜内容
    const hasContent = await page.evaluate(() => {
      return document.querySelector('.HotList-item') !== null || 
             document.querySelector('[class*=HotItem]') !== null ||
             document.body.innerText.includes('热度');
    });
    
    if (hasContent) {
      console.log('  热榜内容可见 ✓');
    }

    const cookies = await context.cookies();
    fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
    console.log(`💾 Cookie 已保存到 ${COOKIE_FILE}`);
    console.log(`   共 ${cookies.length} 个 Cookie`);

    const keyKeys = ['z_c0', 'd_c0', 'zst_82', '_zap'];
    const found = keyKeys.filter(k => cookies.some(c => c.name === k));
    console.log(`   关键 Cookie: ${found.join(', ')}`);
  } catch (e) {
    const cookies = await context.cookies();
    if (cookies.length > 3) {
      fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
      console.log(`\n💾 已保存 ${cookies.length} 个 Cookie (可能未完全登录)`);
    } else {
      console.log('\n⏱️ 超时，请确认已登录后重新运行');
    }
  }

  await context.close();
  console.log('👋 完成!');
})();
