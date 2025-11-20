/**
 * Notifications System JavaScript
 */

let allNotifications = [];
let currentFilter = 'all';
let notificationPollingInterval = null;

// 頁面載入時執行
document.addEventListener('DOMContentLoaded', async () => {
  try {
    // 載入通知統計
    await loadNotificationStats();
    
    // 載入通知列表
    await loadNotifications();
    
    // 開始輪詢 (每 30 秒更新一次)
    startNotificationPolling();
    
  } catch (error) {
    console.error('初始化失敗:', error);
    Utils.showError('載入失敗');
  }
});

// 載入通知統計
async function loadNotificationStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/notifications/stats`, {
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) {
      // 如果 API 不存在,使用模擬資料
      useMockStats();
      return;
    }

    const stats = await response.json();
    
    // 更新統計數據
    document.getElementById('unread-count').textContent = stats.unread || 0;
    document.getElementById('today-count').textContent = stats.today || 0;
    document.getElementById('week-count').textContent = stats.week || 0;
    document.getElementById('total-count').textContent = stats.total || 0;
    
    // 更新導航欄徽章
    updateNavBadge(stats.unread || 0);

  } catch (error) {
    console.error('載入統計失敗:', error);
    useMockStats();
  }
}

// 使用模擬統計資料
function useMockStats() {
  const unreadCount = allNotifications.filter(n => !n.is_read).length;
  
  document.getElementById('unread-count').textContent = unreadCount;
  document.getElementById('today-count').textContent = allNotifications.filter(n => 
    isToday(new Date(n.created_at))
  ).length;
  document.getElementById('week-count').textContent = allNotifications.filter(n => 
    isThisWeek(new Date(n.created_at))
  ).length;
  document.getElementById('total-count').textContent = allNotifications.length;
  
  updateNavBadge(unreadCount);
}

// 更新導航欄徽章
function updateNavBadge(count) {
  const badge = document.getElementById('nav-notification-badge');
  if (badge) {
    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : count;
      badge.style.display = 'block';
    } else {
      badge.style.display = 'none';
    }
  }
}

// 載入通知列表
async function loadNotifications() {
  try {
    const response = await fetch(`${API_BASE_URL}/notifications`, {
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) {
      // 如果 API 不存在,使用模擬資料
      useMockNotifications();
      return;
    }

    allNotifications = await response.json();
    displayNotifications(allNotifications);
    
    // 更新統計
    useMockStats();

  } catch (error) {
    console.error('載入通知失敗:', error);
    useMockNotifications();
  }
}

// 使用模擬通知資料
function useMockNotifications() {
  allNotifications = [
    {
      id: 1,
      type: 'task',
      title: '新任務指派',
      content: '你被指派了新任務「實作登入功能」',
      is_read: false,
      created_at: new Date().toISOString(),
      link: 'task-detail.html?id=1'
    },
    {
      id: 2,
      type: 'comment',
      title: '新評論',
      content: '張三在「網站改版」任務中提到了你',
      is_read: false,
      created_at: new Date(Date.now() - 3600000).toISOString(),
      link: 'task-detail.html?id=2'
    },
    {
      id: 3,
      type: 'project',
      title: '專案更新',
      content: '「行動 App 開發」專案已完成',
      is_read: true,
      created_at: new Date(Date.now() - 86400000).toISOString(),
      link: 'project.html?id=3'
    }
  ];
  
  displayNotifications(allNotifications);
  useMockStats();
}

// 顯示通知列表
function displayNotifications(notifications) {
  const container = document.getElementById('notifications-list');
  
  if (notifications.length === 0) {
    container.innerHTML = '<div class="empty-state">暫無通知</div>';
    return;
  }

  container.innerHTML = notifications.map(notification => `
    <div class="notification-item ${notification.is_read ? 'read' : 'unread'}" 
         data-id="${notification.id}"
         data-type="${notification.type}"
         data-read="${notification.is_read}">
      <div class="notification-icon">${getNotificationIcon(notification.type)}</div>
      <div class="notification-content" onclick="handleNotificationClick(${notification.id}, '${notification.link || '#'}')">
        <div class="notification-header">
          <span class="notification-title">${notification.title}</span>
          <span class="notification-time">${Utils.formatRelativeTime(notification.created_at)}</span>
        </div>
        <div class="notification-body">${notification.content}</div>
      </div>
      <div class="notification-actions">
        ${!notification.is_read ? `
          <button class="icon-btn" onclick="event.stopPropagation(); markAsRead(${notification.id})" title="標記已讀">
            ✓
          </button>
        ` : ''}
        <button class="icon-btn" onclick="event.stopPropagation(); deleteNotification(${notification.id})" title="刪除">
          🗑️
        </button>
      </div>
    </div>
  `).join('');
}

// 取得通知圖示
function getNotificationIcon(type) {
  const icons = {
    'task': '📋',
    'project': '📁',
    'comment': '💬',
    'mention': '@',
    'system': '⚙️',
    'default': '📬'
  };
  return icons[type] || icons.default;
}

// 處理通知點擊
async function handleNotificationClick(notificationId, link) {
  // 標記為已讀
  await markAsRead(notificationId);
  
  // 跳轉到相關頁面
  if (link && link !== '#') {
    window.location.href = link;
  }
}

// 標記單一通知為已讀
async function markAsRead(notificationId) {
  try {
    const response = await fetch(`${API_BASE_URL}/notifications/${notificationId}/read`, {
      method: 'PATCH',
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) {
      // 如果 API 不存在,更新本地資料
      const notification = allNotifications.find(n => n.id === notificationId);
      if (notification) {
        notification.is_read = true;
      }
    }

    // 重新載入通知
    await loadNotifications();
    
  } catch (error) {
    console.error('標記已讀失敗:', error);
    // 仍然更新本地狀態
    const notification = allNotifications.find(n => n.id === notificationId);
    if (notification) {
      notification.is_read = true;
      displayNotifications(allNotifications);
      useMockStats();
    }
  }
}

// 標記全部為已讀
async function markAllAsRead() {
  try {
    const response = await fetch(`${API_BASE_URL}/notifications/read-all`, {
      method: 'PATCH',
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) {
      // 如果 API 不存在,更新本地資料
      allNotifications.forEach(n => n.is_read = true);
    }

    Utils.showSuccess('已全部標記為已讀');
    
    // 重新載入通知
    await loadNotifications();
    
  } catch (error) {
    console.error('標記全部已讀失敗:', error);
    // 仍然更新本地狀態
    allNotifications.forEach(n => n.is_read = true);
    displayNotifications(allNotifications);
    useMockStats();
    Utils.showSuccess('已全部標記為已讀');
  }
}

// 刪除通知
async function deleteNotification(notificationId) {
  if (!confirm('確定要刪除此通知嗎?')) return;

  try {
    const response = await fetch(`${API_BASE_URL}/notifications/${notificationId}`, {
      method: 'DELETE',
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) {
      // 如果 API 不存在,更新本地資料
      allNotifications = allNotifications.filter(n => n.id !== notificationId);
    }

    Utils.showSuccess('通知已刪除');
    
    // 重新載入通知
    await loadNotifications();
    
  } catch (error) {
    console.error('刪除通知失敗:', error);
    // 仍然更新本地狀態
    allNotifications = allNotifications.filter(n => n.id !== notificationId);
    displayNotifications(allNotifications);
    useMockStats();
    Utils.showSuccess('通知已刪除');
  }
}

// 刪除所有已讀通知
async function deleteAllRead() {
  if (!confirm('確定要刪除所有已讀通知嗎?')) return;

  const readNotifications = allNotifications.filter(n => n.is_read);
  
  if (readNotifications.length === 0) {
    Utils.showError('沒有已讀通知');
    return;
  }

  try {
    // 逐一刪除 (如果 API 沒有批次刪除功能)
    for (const notification of readNotifications) {
      await fetch(`${API_BASE_URL}/notifications/${notification.id}`, {
        method: 'DELETE',
        headers: Utils.getAuthHeaders()
      }).catch(() => {
        // 忽略個別錯誤
      });
    }

    Utils.showSuccess(`已刪除 ${readNotifications.length} 則已讀通知`);
    
    // 重新載入通知
    await loadNotifications();
    
  } catch (error) {
    console.error('刪除已讀通知失敗:', error);
    // 仍然更新本地狀態
    allNotifications = allNotifications.filter(n => !n.is_read);
    displayNotifications(allNotifications);
    useMockStats();
    Utils.showSuccess('已讀通知已刪除');
  }
}

// 篩選通知
function filterNotifications(filter) {
  currentFilter = filter;
  
  // 更新按鈕狀態
  document.querySelectorAll('.notification-filters .filter-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.dataset.filter === filter) {
      btn.classList.add('active');
    }
  });

  // 篩選通知
  let filteredNotifications = allNotifications;
  
  if (filter === 'unread') {
    filteredNotifications = allNotifications.filter(n => !n.is_read);
  } else if (filter !== 'all') {
    filteredNotifications = allNotifications.filter(n => n.type === filter);
  }

  displayNotifications(filteredNotifications);
}

// 切換通知下拉選單
function toggleNotificationDropdown() {
  const dropdown = document.getElementById('notification-dropdown');
  
  if (dropdown.style.display === 'none' || !dropdown.style.display) {
    // 顯示下拉選單
    loadRecentNotifications();
    dropdown.style.display = 'block';
  } else {
    // 隱藏下拉選單
    dropdown.style.display = 'none';
  }
}

// 載入最近通知 (下拉選單用)
async function loadRecentNotifications() {
  const recentNotifications = allNotifications.slice(0, 5);
  const container = document.getElementById('recent-notifications');
  
  if (recentNotifications.length === 0) {
    container.innerHTML = '<div class="dropdown-empty">暫無通知</div>';
    return;
  }

  container.innerHTML = recentNotifications.map(notification => `
    <div class="notification-dropdown-item ${notification.is_read ? 'read' : 'unread'}" 
         onclick="handleNotificationClick(${notification.id}, '${notification.link || '#'}')">
      <div class="dropdown-notification-icon">${getNotificationIcon(notification.type)}</div>
      <div class="dropdown-notification-content">
        <div class="dropdown-notification-title">${notification.title}</div>
        <div class="dropdown-notification-body">${notification.content}</div>
        <div class="dropdown-notification-time">${Utils.formatRelativeTime(notification.created_at)}</div>
      </div>
    </div>
  `).join('');
}

// 開始通知輪詢
function startNotificationPolling() {
  // 每 30 秒更新一次
  notificationPollingInterval = setInterval(async () => {
    await loadNotifications();
    await loadNotificationStats();
  }, 30000);
}

// 停止通知輪詢
function stopNotificationPolling() {
  if (notificationPollingInterval) {
    clearInterval(notificationPollingInterval);
    notificationPollingInterval = null;
  }
}

// 判斷是否為今天
function isToday(date) {
  const today = new Date();
  return date.getDate() === today.getDate() &&
         date.getMonth() === today.getMonth() &&
         date.getFullYear() === today.getFullYear();
}

// 判斷是否為本週
function isThisWeek(date) {
  const now = new Date();
  const weekStart = new Date(now.setDate(now.getDate() - now.getDay()));
  weekStart.setHours(0, 0, 0, 0);
  return date >= weekStart;
}

// 登出
function logout() {
  stopNotificationPolling();
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = 'index.html';
}

// 點擊外部關閉下拉選單
window.onclick = function(event) {
  const dropdown = document.getElementById('notification-dropdown');
  const bell = document.querySelector('.notification-bell');
  
  if (dropdown && !dropdown.contains(event.target) && !bell.contains(event.target)) {
    dropdown.style.display = 'none';
  }
};

// 頁面卸載時停止輪詢
window.addEventListener('beforeunload', () => {
  stopNotificationPolling();
});