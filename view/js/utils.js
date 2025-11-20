/**
 * 通用工具函數
 */

const Utils = {
  /**
   * 顯示 Toast 訊息
   */
  showToast(message, type = 'info') {
      // 移除現有 toast
      const existingToast = document.querySelector('.toast');
      if (existingToast) {
          existingToast.remove();
      }

      // 建立新 toast
      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.textContent = message;
      
      document.body.appendChild(toast);

      // 動畫顯示
      setTimeout(() => toast.classList.add('show'), 10);

      // 自動隱藏
      setTimeout(() => {
          toast.classList.remove('show');
          setTimeout(() => toast.remove(), 300);
      }, CONFIG.TOAST_DURATION);
  },

  /**
   * 顯示成功訊息
   */
  showSuccess(message) {
      this.showToast(message, 'success');
  },

  /**
   * 顯示錯誤訊息
   */
  showError(message) {
      this.showToast(message, 'error');
  },

  /**
   * 顯示警告訊息
   */
  showWarning(message) {
      this.showToast(message, 'warning');
  },

  /**
   * 顯示 Loading
   */
  showLoading(text = '載入中...') {
      // 移除現有 loading
      this.hideLoading();

      const loading = document.createElement('div');
      loading.className = 'loading-overlay';
      loading.innerHTML = `
          <div class="loading-spinner">
              <div class="spinner"></div>
              <p>${text}</p>
          </div>
      `;
      
      document.body.appendChild(loading);
  },

  /**
   * 隱藏 Loading
   */
  hideLoading() {
      const loading = document.querySelector('.loading-overlay');
      if (loading) {
          loading.remove();
      }
  },

  /**
   * 確認對話框
   */
  confirm(message, onConfirm, onCancel) {
      const modal = document.createElement('div');
      modal.className = 'modal confirm-modal';
      modal.innerHTML = `
          <div class="modal-content">
              <h3>確認</h3>
              <p>${message}</p>
              <div class="modal-actions">
                  <button class="btn-primary confirm-btn">確定</button>
                  <button class="btn-secondary cancel-btn">取消</button>
              </div>
          </div>
      `;

      document.body.appendChild(modal);

      // 綁定事件
      modal.querySelector('.confirm-btn').onclick = () => {
          modal.remove();
          if (onConfirm) onConfirm();
      };

      modal.querySelector('.cancel-btn').onclick = () => {
          modal.remove();
          if (onCancel) onCancel();
      };

      // 點擊背景關閉
      modal.onclick = (e) => {
          if (e.target === modal) {
              modal.remove();
              if (onCancel) onCancel();
          }
      };
  },

  /**
   * 格式化日期
   */
  formatDate(dateString, format = CONFIG.DATE_FORMAT) {
      if (!dateString) return '';
      
      const date = new Date(dateString);
      
      if (format === 'relative') {
          return this.getRelativeTime(date);
      }

      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');

      return format
          .replace('YYYY', year)
          .replace('MM', month)
          .replace('DD', day)
          .replace('HH', hours)
          .replace('mm', minutes)
          .replace('ss', seconds);
  },

  /**
   * 取得相對時間（如：3 天前）
   */
  getRelativeTime(date) {
      const now = new Date();
      const diffMs = now - new Date(date);
      const diffSec = Math.floor(diffMs / 1000);
      const diffMin = Math.floor(diffSec / 60);
      const diffHour = Math.floor(diffMin / 60);
      const diffDay = Math.floor(diffHour / 24);

      if (diffSec < 60) return '剛剛';
      if (diffMin < 60) return `${diffMin} 分鐘前`;
      if (diffHour < 24) return `${diffHour} 小時前`;
      if (diffDay < 7) return `${diffDay} 天前`;
      if (diffDay < 30) return `${Math.floor(diffDay / 7)} 週前`;
      if (diffDay < 365) return `${Math.floor(diffDay / 30)} 個月前`;
      return `${Math.floor(diffDay / 365)} 年前`;
  },

  /**
   * 防抖函數
   */
  debounce(func, delay = CONFIG.DEBOUNCE_DELAY) {
      let timeoutId;
      return function (...args) {
          clearTimeout(timeoutId);
          timeoutId = setTimeout(() => func.apply(this, args), delay);
      };
  },

  /**
   * 節流函數
   */
  throttle(func, limit = 1000) {
      let inThrottle;
      return function (...args) {
          if (!inThrottle) {
              func.apply(this, args);
              inThrottle = true;
              setTimeout(() => (inThrottle = false), limit);
          }
      };
  },

  /**
   * 檢查是否已登入
   */
  isAuthenticated() {
      return !!localStorage.getItem(CONFIG.TOKEN_KEY);
  },

  /**
   * 取得當前使用者
   */
  getCurrentUser() {
      const userStr = localStorage.getItem(CONFIG.USER_KEY);
      return userStr ? JSON.parse(userStr) : null;
  },

  /**
   * 檢查權限
   */
  hasRole(project, role) {
      const user = this.getCurrentUser();
      if (!user) return false;

      if (role === 'owner') {
          return project.owner_id === user.id;
      }

      if (role === 'admin') {
          return project.my_role === 'admin' || project.owner_id === user.id;
      }

      return true; // member 或以上
  },

  /**
   * 轉義 HTML 特殊字元
   */
  escapeHtml(text) {
      const map = {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#039;'
      };
      return text.replace(/[&<>"']/g, (m) => map[m]);
  },

  /**
   * 驗證 Email 格式
   */
  isValidEmail(email) {
      const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return regex.test(email);
  },

  /**
   * 驗證密碼強度
   */
  validatePassword(password) {
      const errors = [];

      if (password.length < 8) {
          errors.push('密碼至少需要 8 個字元');
      }

      if (!/[A-Z]/.test(password)) {
          errors.push('密碼需要包含至少一個大寫字母');
      }

      if (!/[a-z]/.test(password)) {
          errors.push('密碼需要包含至少一個小寫字母');
      }

      if (!/[0-9]/.test(password)) {
          errors.push('密碼需要包含至少一個數字');
      }

      return {
          isValid: errors.length === 0,
          errors
      };
  },

  /**
   * 取得任務狀態文字
   */
  getTaskStatusText(status) {
      const map = {
          [CONFIG.TASK_STATUS.TODO]: '待處理',
          [CONFIG.TASK_STATUS.IN_PROGRESS]: '進行中',
          [CONFIG.TASK_STATUS.DONE]: '已完成'
      };
      return map[status] || status;
  },

  /**
   * 取得任務優先級文字
   */
  getTaskPriorityText(priority) {
      const map = {
          [CONFIG.TASK_PRIORITY.LOW]: '低',
          [CONFIG.TASK_PRIORITY.MEDIUM]: '中',
          [CONFIG.TASK_PRIORITY.HIGH]: '高'
      };
      return map[priority] || priority;
  },

  /**
   * 取得優先級顏色類別
   */
  getPriorityClass(priority) {
      return `badge-${priority}`;
  },

  /**
   * 取得角色文字
   */
  getRoleText(role) {
      const map = {
          [CONFIG.PROJECT_ROLES.OWNER]: '擁有者',
          [CONFIG.PROJECT_ROLES.ADMIN]: '管理員',
          [CONFIG.PROJECT_ROLES.MEMBER]: '成員'
      };
      return map[role] || role;
  },

  /**
   * 複製到剪貼簿
   */
  async copyToClipboard(text) {
      try {
          await navigator.clipboard.writeText(text);
          this.showSuccess('已複製到剪貼簿');
      } catch (error) {
          console.error('複製失敗:', error);
          this.showError('複製失敗');
      }
  },

  /**
   * 下載檔案
   */
  downloadFile(url, filename) {
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
  },

  /**
   * 取得查詢參數
   */
  getQueryParam(name) {
      const urlParams = new URLSearchParams(window.location.search);
      return urlParams.get(name);
  },

  /**
   * 設定查詢參數
   */
  setQueryParam(name, value) {
      const url = new URL(window.location);
      url.searchParams.set(name, value);
      window.history.pushState({}, '', url);
  },

  /**
   * 清空表單
   */
  clearForm(formElement) {
      if (typeof formElement === 'string') {
          formElement = document.querySelector(formElement);
      }
      if (formElement) {
          formElement.reset();
      }
  },

  /**
   * 平滑捲動到元素
   */
  scrollToElement(element, offset = 0) {
      if (typeof element === 'string') {
          element = document.querySelector(element);
      }
      if (element) {
          const top = element.offsetTop - offset;
          window.scrollTo({ top, behavior: 'smooth' });
      }
  }
};

// 在頁面載入時檢查登入狀態
document.addEventListener('DOMContentLoaded', () => {
  // 如果在登入頁以外的頁面且未登入，跳轉到登入頁
  const isLoginPage = window.location.pathname.includes('index.html') || 
                     window.location.pathname === '/' ||
                     window.location.pathname === '';
  
  if (!isLoginPage && !Utils.isAuthenticated()) {
      window.location.href = 'index.html';
  }
});