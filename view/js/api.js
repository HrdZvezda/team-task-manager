/**
 * API 請求封裝
 * 統一處理所有 API 請求、錯誤處理、token 管理
 */

class APIClient {
  constructor(baseURL) {
      this.baseURL = baseURL;
  }

  /**
   * 取得 token
   */
  getToken() {
      return localStorage.getItem(CONFIG.TOKEN_KEY);
  }

  /**
   * 取得 refresh token
   */
  getRefreshToken() {
      return localStorage.getItem(CONFIG.REFRESH_TOKEN_KEY);
  }

  /**
   * 儲存 tokens
   */
  saveTokens(accessToken, refreshToken) {
      localStorage.setItem(CONFIG.TOKEN_KEY, accessToken);
      if (refreshToken) {
          localStorage.setItem(CONFIG.REFRESH_TOKEN_KEY, refreshToken);
      }
  }

  /**
   * 清除所有認證資訊
   */
  clearAuth() {
      localStorage.removeItem(CONFIG.TOKEN_KEY);
      localStorage.removeItem(CONFIG.REFRESH_TOKEN_KEY);
      localStorage.removeItem(CONFIG.USER_KEY);
  }

  /**
   * 跳轉到登入頁
   */
  redirectToLogin() {
      this.clearAuth();
      window.location.href = 'index.html';
  }

  /**
   * 刷新 access token
   */
  async refreshAccessToken() {
      const refreshToken = this.getRefreshToken();
      
      if (!refreshToken) {
          throw new Error('No refresh token available');
      }

      try {
          const response = await fetch(`${this.baseURL}/auth/refresh`, {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${refreshToken}`
              }
          });

          if (!response.ok) {
              throw new Error('Token refresh failed');
          }

          const data = await response.json();
          
          // 儲存新的 access token
          this.saveTokens(data.access_token);
          
          return data.access_token;
      } catch (error) {
          console.error('Token refresh error:', error);
          throw error;
      }
  }

  /**
   * 統一的請求方法
   */
  async request(endpoint, options = {}, retryCount = 0) {
      const url = `${this.baseURL}${endpoint}`;
      const token = this.getToken();
      
      // 預設選項
      const defaultOptions = {
          headers: {
              'Content-Type': 'application/json',
              ...(token && { 'Authorization': `Bearer ${token}` })
          }
      };

      // 合併選項
      const finalOptions = {
          ...defaultOptions,
          ...options,
          headers: {
              ...defaultOptions.headers,
              ...options.headers
          }
      };

      try {
          // 加上 timeout 控制
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);
          
          finalOptions.signal = controller.signal;

          const response = await fetch(url, finalOptions);
          
          clearTimeout(timeoutId);

          // 處理 401 未授權
          if (response.status === 401 && retryCount === 0) {
              try {
                  // 嘗試刷新 token
                  await this.refreshAccessToken();
                  // 重試原請求
                  return await this.request(endpoint, options, retryCount + 1);
              } catch (refreshError) {
                  // 刷新失敗，跳轉登入頁
                  this.redirectToLogin();
                  throw new Error(CONFIG.ERROR_MESSAGES.UNAUTHORIZED);
              }
          }

          // 處理其他 HTTP 錯誤
          if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              const errorMessage = errorData.error || errorData.message || this.getErrorMessage(response.status);
              throw new Error(errorMessage);
          }

          // 成功回應
          return await response.json();

      } catch (error) {
          // 處理網路錯誤
          if (error.name === 'AbortError') {
              throw new Error(CONFIG.ERROR_MESSAGES.TIMEOUT);
          }
          
          if (error instanceof TypeError) {
              throw new Error(CONFIG.ERROR_MESSAGES.NETWORK_ERROR);
          }

          // 重新拋出其他錯誤
          throw error;
      }
  }

  /**
   * 根據 HTTP 狀態碼取得錯誤訊息
   */
  getErrorMessage(status) {
      const messages = {
          400: '請求參數錯誤',
          401: CONFIG.ERROR_MESSAGES.UNAUTHORIZED,
          403: CONFIG.ERROR_MESSAGES.FORBIDDEN,
          404: CONFIG.ERROR_MESSAGES.NOT_FOUND,
          429: '請求過於頻繁，請稍後再試',
          500: CONFIG.ERROR_MESSAGES.SERVER_ERROR,
          503: '服務暫時無法使用，請稍後再試'
      };

      return messages[status] || CONFIG.ERROR_MESSAGES.UNKNOWN_ERROR;
  }

  /**
   * GET 請求
   */
  async get(endpoint, params = {}) {
      // 將參數轉換為 query string
      const queryString = new URLSearchParams(params).toString();
      const fullEndpoint = queryString ? `${endpoint}?${queryString}` : endpoint;
      
      return this.request(fullEndpoint, { method: 'GET' });
  }

  /**
   * POST 請求
   */
  async post(endpoint, data = {}) {
      return this.request(endpoint, {
          method: 'POST',
          body: JSON.stringify(data)
      });
  }

  /**
   * PATCH 請求
   */
  async patch(endpoint, data = {}) {
      return this.request(endpoint, {
          method: 'PATCH',
          body: JSON.stringify(data)
      });
  }

  /**
   * DELETE 請求
   */
  async delete(endpoint) {
      return this.request(endpoint, {
          method: 'DELETE'
      });
  }

  /**
   * 檔案上傳
   */
  async upload(endpoint, formData) {
      const token = this.getToken();
      
      return this.request(endpoint, {
          method: 'POST',
          headers: {
              // 不設定 Content-Type，讓瀏覽器自動設定 multipart/form-data
              ...(token && { 'Authorization': `Bearer ${token}` })
          },
          body: formData
      });
  }
}

// 建立全域 API 實例
const api = new APIClient(CONFIG.API_URL);

// 匯出常用的 API 方法
const AuthAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  updateMe: (data) => api.patch('/auth/me', data),
  changePassword: (data) => api.post('/auth/change-password', data),
  refresh: () => api.post('/auth/refresh')
};

const ProjectAPI = {
  list: () => api.get('/projects'),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.patch(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
  getStats: (id) => api.get(`/projects/${id}/stats`),
  
  // 成員管理
  listMembers: (id) => api.get(`/projects/${id}/members`),
  addMember: (id, data) => api.post(`/projects/${id}/members`, data),
  updateMember: (projectId, memberId, data) => api.patch(`/projects/${projectId}/members/${memberId}`, data),
  removeMember: (projectId, memberId) => api.delete(`/projects/${projectId}/members/${memberId}`)
};

const TaskAPI = {
  list: (projectId) => api.get(`/projects/${projectId}/tasks`),
  myTasks: () => api.get('/tasks/my'),
  get: (id) => api.get(`/tasks/${id}`),
  create: (projectId, data) => api.post(`/projects/${projectId}/tasks`, data),
  update: (id, data) => api.patch(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
  
  // 評論
  listComments: (id) => api.get(`/tasks/${id}/comments`),
  addComment: (id, data) => api.post(`/tasks/${id}/comments`, data)
};

const NotificationAPI = {
  list: (params) => api.get('/api/notifications', params),
  markRead: (id) => api.patch(`/api/notifications/${id}/read`),
  markAllRead: () => api.patch('/api/notifications/read-all'),
  delete: (id) => api.delete(`/api/notifications/${id}`),
  clear: () => api.delete('/api/notifications/clear'),
  getSettings: () => api.get('/api/notifications/settings'),
  updateSettings: (data) => api.patch('/api/notifications/settings', data),
  getStats: () => api.get('/api/notifications/stats')
};

// 3.4 Token 自動刷新
// 修改檔案: view/js/api.js
// 需要串接的 API:

// POST /auth/refresh - 刷新 token

// 功能需求:
// javascript// 在 api.js 加上自動刷新邏輯
// class APIClient {
//     async request(endpoint, options = {}) {
//         try {
//             const response = await fetch(url, finalOptions);
            
//             // 如果 401 且有 refresh_token,嘗試刷新
//             if (response.status === 401) {
//                 const refreshToken = localStorage.getItem('refresh_token');
//                 if (refreshToken) {
//                     const newToken = await this.refreshToken();
//                     if (newToken) {
//                         // 重試原本的請求
//                         return this.request(endpoint, options);
//                     }
//                 }
//                 // 刷新失敗,跳轉登入頁
//                 this.logout();
//             }
            
//             return await response.json();
//         } catch (error) {
//             throw error;
//         }
//     }
    
//     async refreshToken() {
//         // 實作 token 刷新邏輯
//     }
// }
// 開發步驟:

//  登入時儲存 refresh_token
//  實作 refreshToken() 方法
//  在 request() 中加上自動刷新邏輯
//  測試 token 過期情境