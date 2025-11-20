/**
 * 前端設定檔
 * 集中管理所有設定項目
 */

const CONFIG = {
  // API 基礎 URL
  // 會根據環境自動切換
  API_URL: (() => {
      const hostname = window.location.hostname;
      
      // 本地開發環境
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
          return 'http://127.0.0.1:8888';
      }
      
      // 生產環境 (請替換成你的實際 API 網址)
      return 'https://team-task-manager-lr5e.onrender.com';
  })(),
  
  // Token 儲存的 key
  TOKEN_KEY: 'token',
  REFRESH_TOKEN_KEY: 'refresh_token',
  USER_KEY: 'user',
  
  // API timeout 設定 (毫秒)
  REQUEST_TIMEOUT: 30000,
  
  // 分頁設定
  DEFAULT_PAGE_SIZE: 20,
  
  // 日期格式
  DATE_FORMAT: 'YYYY-MM-DD',
  DATETIME_FORMAT: 'YYYY-MM-DD HH:mm:ss',
  
  // 錯誤訊息
  ERROR_MESSAGES: {
      NETWORK_ERROR: '網路連線錯誤，請檢查您的網路狀態',
      TIMEOUT: '請求逾時，請稍後再試',
      UNAUTHORIZED: '登入已過期，請重新登入',
      FORBIDDEN: '沒有權限執行此操作',
      NOT_FOUND: '找不到請求的資源',
      SERVER_ERROR: '伺服器錯誤，請稍後再試',
      UNKNOWN_ERROR: '發生未知錯誤，請稍後再試'
  },
  
  // UI 設定
  TOAST_DURATION: 3000, // Toast 訊息顯示時間
  DEBOUNCE_DELAY: 300,  // 防抖延遲時間
  
  // 任務狀態
  TASK_STATUS: {
      TODO: 'todo',
      IN_PROGRESS: 'in_progress',
      DONE: 'done'
  },
  
  // 任務優先級
  TASK_PRIORITY: {
      LOW: 'low',
      MEDIUM: 'medium',
      HIGH: 'high'
  },
  
  // 專案角色
  PROJECT_ROLES: {
      OWNER: 'owner',
      ADMIN: 'admin',
      MEMBER: 'member'
  }
};

// 凍結設定物件，防止被修改
Object.freeze(CONFIG);