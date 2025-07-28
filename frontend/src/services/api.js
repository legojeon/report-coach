import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
});

// 응답 인터셉터 추가
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // 401 에러 시 로그인 페이지로 리다이렉트
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 토큰 사용량 조회
export const getTokenUsage = async (token, params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.service_name) {
    queryParams.append('service_name', params.service_name);
  }
  if (params.start_date) {
    queryParams.append('start_date', params.start_date);
  }
  if (params.end_date) {
    queryParams.append('end_date', params.end_date);
  }
  
  const response = await api.get(`/logger/ai-usage?${queryParams.toString()}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// 사용자 기록 조회
export const getUserHistory = async (token, params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.service_type) {
    queryParams.append('service_type', params.service_type);
  }
  
  const response = await api.get(`/logger/history?${queryParams.toString()}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// 사용자 노트 조회
export const getUserNotes = async (token) => {
  const response = await api.get('/notes/', {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// 노트 업데이트 또는 생성
export const updateOrCreateNote = async (token, noteData) => {
  const response = await api.post('/notes/update_or_create', noteData, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// 노트 비활성화 (soft delete)
export const deactivateNote = async (token, noteId) => {
  const response = await api.patch(`/notes/deactivate/${noteId}`, {}, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// 채팅 히스토리 조회
export const getChatHistory = async (token, reportNumber) => {
  const response = await api.get(`/chat/history/${reportNumber}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// WritePage 채팅 (세션 기반)
export const chatWithWrite = async (token, message, userReport = "", history = null) => {
  const requestData = { 
    message, 
    user_report: userReport 
  };
  
  // 히스토리가 있으면 추가
  if (history) {
    requestData.history = history;
  }
  
  const response = await api.post('/write/chat', requestData, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// WritePage 채팅 히스토리 조회
export const getWriteChatHistory = async (token) => {
  const response = await api.get('/write/history', {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

// WritePage 채팅 히스토리 정리
export const cleanupWriteSession = async (token) => {
  const response = await api.delete('/write/session', {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

export default api; 