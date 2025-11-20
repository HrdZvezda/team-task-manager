/**
 * Task Detail Page JavaScript
 */

let currentTask = null;
let currentProject = null;
let projectMembers = [];

// 從 URL 取得任務 ID
function getTaskIdFromURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

// 從 URL 取得專案 ID
function getProjectIdFromURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get('project');
}

// 頁面載入時執行
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const taskId = getTaskIdFromURL();
    const projectId = getProjectIdFromURL();
    
    if (!taskId) {
      Utils.showError('找不到任務 ID');
      setTimeout(() => window.location.href = 'dashboard.html', 2000);
      return;
    }

    // 載入任務詳情
    await loadTaskDetail(taskId, projectId);
    
    // 載入評論
    await loadComments(taskId);
    
    // 載入活動記錄
    await loadActivityLog(taskId);
    
    // 如果有專案 ID，載入專案成員
    if (projectId) {
      await loadProjectMembers(projectId);
    }
  } catch (error) {
    console.error('初始化失敗:', error);
    Utils.showError('載入失敗');
  }
});

// 載入任務詳情
async function loadTaskDetail(taskId, projectId) {
  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) throw new Error('載入任務失敗');

    const data = await response.json();
    currentTask = data;

    // 更新頁面內容
    document.getElementById('detail-task-title').textContent = data.title;
    document.getElementById('detail-description').textContent = data.description || '無描述';
    document.getElementById('task-name').textContent = data.title;
    
    // 狀態
    const statusBadge = document.getElementById('detail-status');
    statusBadge.textContent = getStatusText(data.status);
    statusBadge.className = `task-status-badge status-${data.status}`;
    
    // 優先級
    const priorityEl = document.getElementById('detail-priority');
    priorityEl.textContent = getPriorityText(data.priority);
    priorityEl.className = `task-priority priority-${data.priority}`;
    
    // 負責人
    updateAssigneeInfo(data.assigned_to);
    
    // 時間資訊
    document.getElementById('detail-created-at').textContent = 
      Utils.formatDate(data.created_at, 'YYYY-MM-DD HH:mm');
    document.getElementById('detail-updated-at').textContent = 
      Utils.formatDate(data.updated_at, 'YYYY-MM-DD HH:mm');
    document.getElementById('detail-due-date').textContent = 
      data.due_date ? Utils.formatDate(data.due_date, 'YYYY-MM-DD') : '未設定';

    // 如果有專案資訊，更新麵包屑
    if (projectId) {
      await loadProjectInfo(projectId);
    }

    // 載入附件
    if (data.attachments && data.attachments.length > 0) {
      displayAttachments(data.attachments);
    } else {
      document.getElementById('attachments-list').innerHTML = 
        '<p class="empty-state">暫無附件</p>';
    }

    // 載入標籤
    if (data.tags && data.tags.length > 0) {
      displayTags(data.tags);
    } else {
      document.getElementById('tags-list').innerHTML = 
        '<p class="empty-state">暫無標籤</p>';
    }

  } catch (error) {
    console.error('載入任務詳情失敗:', error);
    Utils.showError('載入任務詳情失敗');
  }
}

// 載入專案資訊
async function loadProjectInfo(projectId) {
  try {
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}`, {
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) throw new Error('載入專案失敗');

    const project = await response.json();
    currentProject = project;

    // 更新麵包屑
    const projectLink = document.getElementById('project-link');
    projectLink.textContent = project.name;
    projectLink.href = `project.html?id=${projectId}`;
  } catch (error) {
    console.error('載入專案資訊失敗:', error);
  }
}

// 更新負責人資訊
function updateAssigneeInfo(assignee) {
  const assigneeInfo = document.getElementById('assignee-info');
  
  if (assignee) {
    assigneeInfo.innerHTML = `
      <div class="member-card">
        <div class="member-avatar">${assignee.username.charAt(0).toUpperCase()}</div>
        <div class="member-info">
          <div class="member-name">${assignee.username}</div>
          <div class="member-email">${assignee.email}</div>
        </div>
      </div>
    `;
  } else {
    assigneeInfo.innerHTML = '<p class="empty-state">未指派</p>';
  }
}

// 載入評論
async function loadComments(taskId) {
  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/comments`, {
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) throw new Error('載入評論失敗');

    const comments = await response.json();
    
    // 更新評論數量
    document.getElementById('comments-count').textContent = `(${comments.length})`;
    
    // 顯示評論
    const commentsList = document.getElementById('comments-list');
    
    if (comments.length === 0) {
      commentsList.innerHTML = '<p class="empty-state">暫無評論</p>';
      return;
    }

    commentsList.innerHTML = comments.map(comment => `
      <div class="comment-item">
        <div class="comment-header">
          <div class="comment-avatar">${comment.user.username.charAt(0).toUpperCase()}</div>
          <div class="comment-meta">
            <span class="comment-author">${comment.user.username}</span>
            <span class="comment-time">${Utils.formatDate(comment.created_at, 'YYYY-MM-DD HH:mm')}</span>
          </div>
        </div>
        <div class="comment-body">${comment.content}</div>
      </div>
    `).join('');

  } catch (error) {
    console.error('載入評論失敗:', error);
  }
}

// 新增評論
async function addComment() {
  const content = document.getElementById('new-comment').value.trim();
  
  if (!content) {
    Utils.showError('請輸入評論內容');
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${currentTask.id}/comments`, {
      method: 'POST',
      headers: Utils.getAuthHeaders(),
      body: JSON.stringify({ content })
    });

    if (!response.ok) throw new Error('新增評論失敗');

    Utils.showSuccess('評論已新增');
    document.getElementById('new-comment').value = '';
    
    // 重新載入評論
    await loadComments(currentTask.id);

  } catch (error) {
    console.error('新增評論失敗:', error);
    Utils.showError('新增評論失敗');
  }
}

// 載入活動記錄
async function loadActivityLog(taskId) {
  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/activity`, {
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) {
      // 如果 API 不存在，顯示空狀態
      document.getElementById('activity-list').innerHTML = 
        '<p class="empty-state">暫無活動記錄</p>';
      return;
    }

    const activities = await response.json();
    
    const activityList = document.getElementById('activity-list');
    
    if (activities.length === 0) {
      activityList.innerHTML = '<p class="empty-state">暫無活動記錄</p>';
      return;
    }

    activityList.innerHTML = activities.map(activity => `
      <div class="activity-item">
        <div class="activity-icon">${getActivityIcon(activity.type)}</div>
        <div class="activity-content">
          <div class="activity-text">${activity.description}</div>
          <div class="activity-time">${Utils.formatDate(activity.created_at, 'YYYY-MM-DD HH:mm')}</div>
        </div>
      </div>
    `).join('');

  } catch (error) {
    console.error('載入活動記錄失敗:', error);
    document.getElementById('activity-list').innerHTML = 
      '<p class="empty-state">暫無活動記錄</p>';
  }
}

// 取得活動圖示
function getActivityIcon(type) {
  const icons = {
    'created': '✨',
    'updated': '✏️',
    'status_changed': '🔄',
    'assigned': '👤',
    'commented': '💬',
    'attached': '📎'
  };
  return icons[type] || '•';
}

// 顯示附件
function displayAttachments(attachments) {
  const attachmentsList = document.getElementById('attachments-list');
  
  attachmentsList.innerHTML = attachments.map(attachment => `
    <div class="attachment-item">
      <div class="attachment-icon">${getFileIcon(attachment.file_type)}</div>
      <div class="attachment-info">
        <div class="attachment-name">${attachment.file_name}</div>
        <div class="attachment-size">${formatFileSize(attachment.file_size)}</div>
      </div>
      <a href="${attachment.file_url}" class="attachment-download" download>下載</a>
    </div>
  `).join('');
}

// 取得檔案圖示
function getFileIcon(fileType) {
  if (fileType.includes('image')) return '🖼️';
  if (fileType.includes('pdf')) return '📄';
  if (fileType.includes('word')) return '📝';
  if (fileType.includes('excel')) return '📊';
  return '📎';
}

// 格式化檔案大小
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 顯示標籤
function displayTags(tags) {
  const tagsList = document.getElementById('tags-list');
  
  tagsList.innerHTML = tags.map(tag => `
    <span class="tag" style="background-color: ${tag.color || '#e0e0e0'}">
      ${tag.name}
    </span>
  `).join('');
}

// 取得狀態文字
function getStatusText(status) {
  const statusMap = {
    'todo': '待處理',
    'in_progress': '進行中',
    'done': '已完成'
  };
  return statusMap[status] || status;
}

// 取得優先級文字
function getPriorityText(priority) {
  const priorityMap = {
    'low': '低',
    'medium': '中',
    'high': '高'
  };
  return priorityMap[priority] || priority;
}

// 編輯任務
function editTask() {
  // 填入當前資料
  document.getElementById('edit-title').value = currentTask.title;
  document.getElementById('edit-description').value = currentTask.description || '';
  document.getElementById('edit-status').value = currentTask.status;
  document.getElementById('edit-priority').value = currentTask.priority;
  
  if (currentTask.due_date) {
    document.getElementById('edit-due-date').value = currentTask.due_date.split('T')[0];
  }
  
  // 顯示 Modal
  document.getElementById('edit-task-modal').style.display = 'flex';
}

// 關閉編輯 Modal
function closeEditModal() {
  document.getElementById('edit-task-modal').style.display = 'none';
}

// 處理編輯表單提交
document.getElementById('edit-task-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const updatedData = {
    title: document.getElementById('edit-title').value,
    description: document.getElementById('edit-description').value,
    status: document.getElementById('edit-status').value,
    priority: document.getElementById('edit-priority').value,
    due_date: document.getElementById('edit-due-date').value || null
  };

  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${currentTask.id}`, {
      method: 'PUT',
      headers: Utils.getAuthHeaders(),
      body: JSON.stringify(updatedData)
    });

    if (!response.ok) throw new Error('更新任務失敗');

    Utils.showSuccess('任務已更新');
    closeEditModal();
    
    // 重新載入任務詳情
    await loadTaskDetail(currentTask.id, getProjectIdFromURL());

  } catch (error) {
    console.error('更新任務失敗:', error);
    Utils.showError('更新任務失敗');
  }
});

// 刪除任務
async function deleteTask() {
  if (!confirm('確定要刪除此任務嗎？')) return;

  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${currentTask.id}`, {
      method: 'DELETE',
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) throw new Error('刪除任務失敗');

    Utils.showSuccess('任務已刪除');
    
    // 返回專案頁面或任務列表
    const projectId = getProjectIdFromURL();
    if (projectId) {
      setTimeout(() => window.location.href = `project.html?id=${projectId}`, 1500);
    } else {
      setTimeout(() => window.location.href = 'my-tasks.html', 1500);
    }

  } catch (error) {
    console.error('刪除任務失敗:', error);
    Utils.showError('刪除任務失敗');
  }
}

// 載入專案成員
async function loadProjectMembers(projectId) {
  try {
    const response = await fetch(`${API_BASE_URL}/projects/${projectId}/members`, {
      headers: Utils.getAuthHeaders()
    });

    if (!response.ok) throw new Error('載入成員失敗');

    projectMembers = await response.json();

  } catch (error) {
    console.error('載入專案成員失敗:', error);
  }
}

// 更改負責人
function changeAssignee() {
  // 填入成員選項
  const select = document.getElementById('new-assignee');
  select.innerHTML = '<option value="">未指派</option>' + 
    projectMembers.map(member => `
      <option value="${member.user_id}" ${currentTask.assigned_to?.id === member.user_id ? 'selected' : ''}>
        ${member.username}
      </option>
    `).join('');
  
  // 顯示 Modal
  document.getElementById('change-assignee-modal').style.display = 'flex';
}

// 關閉更改負責人 Modal
function closeChangeAssigneeModal() {
  document.getElementById('change-assignee-modal').style.display = 'none';
}

// 更新負責人
async function updateAssignee() {
  const newAssigneeId = document.getElementById('new-assignee').value;

  try {
    const response = await fetch(`${API_BASE_URL}/tasks/${currentTask.id}`, {
      method: 'PUT',
      headers: Utils.getAuthHeaders(),
      body: JSON.stringify({
        assigned_to: newAssigneeId || null
      })
    });

    if (!response.ok) throw new Error('更新負責人失敗');

    Utils.showSuccess('負責人已更新');
    closeChangeAssigneeModal();
    
    // 重新載入任務詳情
    await loadTaskDetail(currentTask.id, getProjectIdFromURL());

  } catch (error) {
    console.error('更新負責人失敗:', error);
    Utils.showError('更新負責人失敗');
  }
}

// 上傳附件（待實作）
function uploadAttachment() {
  Utils.showError('附件上傳功能開發中');
}

// 修改截止日期（待實作）
function changeDueDate() {
  Utils.showError('此功能開發中');
}

// 管理標籤（待實作）
function manageTags() {
  Utils.showError('標籤管理功能開發中');
}

// 連結任務（待實作）
function linkTask() {
  Utils.showError('任務連結功能開發中');
}

// 登出
function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.href = 'index.html';
}

// 點擊 Modal 外部關閉
window.onclick = function(event) {
  const editModal = document.getElementById('edit-task-modal');
  const assigneeModal = document.getElementById('change-assignee-modal');
  
  if (event.target === editModal) {
    closeEditModal();
  }
  if (event.target === assigneeModal) {
    closeChangeAssigneeModal();
  }
};