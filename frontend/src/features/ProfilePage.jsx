import React, { useEffect, useState } from 'react';
import { getMe, deleteAccount } from '../services/auth';
import { getTokenUsage, getUserHistory } from '../services/api';
import { useNavigate } from 'react-router-dom';

function ProfilePage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenUsage, setTokenUsage] = useState(null);
  const [tokenLoading, setTokenLoading] = useState(false);
  const [viewType, setViewType] = useState('service'); // 'service' or 'period'
  const [selectedService, setSelectedService] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [userHistory, setUserHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyType, setHistoryType] = useState('all'); // 'all', 'search', 'chat'
  const [showContactModal, setShowContactModal] = useState(false);
  const navigate = useNavigate();

  // Bootstrap SVG 아이콘
  const personCircle = (
    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="#1D4ED8" viewBox="0 0 16 16" className="bg-blue-100 rounded-full p-1">
      <path d="M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0" />
      <path fillRule="evenodd" d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8m8-7a7 7 0 0 0-5.468 11.37C3.242 11.226 4.805 10 8 10s4.757 1.225 5.468 2.37A7 7 0 0 0 8 1" />
    </svg>
  );

  useEffect(() => {
    const fetchUser = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        localStorage.removeItem('token'); // 토큰 제거
        navigate('/');
        return;
      }
      try {
        const data = await getMe(token);
        setUser(data);
      } catch (err) {
        if (err.response && err.response.status === 401) {
          localStorage.removeItem('token');
          navigate('/');
        } else {
          localStorage.removeItem('token'); // 에러 발생 시 토큰 제거
          navigate('/');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [navigate]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-white text-gray-900">로딩 중...</div>;
  }
  // 에러 표시 부분 제거
  if (!user) return null;

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  const handleBack = () => {
    navigate('/');
  };

  const handleWriteClick = () => {
    navigate('/write');
  };

  const handleDeleteAccount = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      console.log('로그인이 필요합니다.');
      localStorage.removeItem('token'); // 토큰 제거
      navigate('/');
      return;
    }

    setDeleteLoading(true);
    try {
      await deleteAccount(token, user.id);
      localStorage.removeItem('token');
      setShowDeleteModal(false);
      navigate('/');
    } catch (err) {
      localStorage.removeItem('token'); // 에러 발생 시 토큰 제거
      navigate('/');
      setShowDeleteModal(false);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleTokenUsage = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      console.log('로그인이 필요합니다.');
      localStorage.removeItem('token'); // 토큰 제거
      navigate('/');
      return;
    }

    setTokenLoading(true);
    setShowTokenModal(true);
    
    try {
      const params = {};
      if (viewType === 'service' && selectedService) {
        params.service_name = selectedService;
      }
      if (viewType === 'period') {
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
      }
      
      const data = await getTokenUsage(token, params);
      setTokenUsage(data);
    } catch (err) {
      console.log('토큰 사용량을 불러오지 못했습니다.');
      localStorage.removeItem('token'); // 에러 발생 시 토큰 제거
      navigate('/');
      console.error('Token usage error:', err);
    } finally {
      setTokenLoading(false);
    }
  };

  const handleFilterChange = async () => {
    if (!showTokenModal) return;
    await handleTokenUsage();
  };

  const getServiceDisplayName = (serviceName) => {
    const serviceNames = {
      'query_summary': '검색 분석',
      'analyze_reports': '보고서 분석',
      'chat_report': '보고서 채팅',
      'write_chat': '보고서 작성'
    };
    return serviceNames[serviceName] || serviceName;
  };

  const handleHistoryView = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      console.log('로그인이 필요합니다.');
      localStorage.removeItem('token'); // 토큰 제거
      navigate('/');
      return;
    }

    setHistoryLoading(true);
    setShowHistoryModal(true);
    
    try {
      const data = await getUserHistory(token, { service_type: historyType });
      setUserHistory(data);
    } catch (err) {
      console.log('기록을 불러오지 못했습니다.');
      localStorage.removeItem('token'); // 에러 발생 시 토큰 제거
      navigate('/');
      console.error('History error:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleHistoryFilterChange = async () => {
    if (!showHistoryModal) return;
    await handleHistoryView();
  };

  return (
    <div className="min-h-screen bg-white text-gray-900 flex flex-col items-center py-12 relative w-full">
      {/* 왼쪽 상단 뒤로가기 버튼 */}
      <button onClick={handleBack} className="absolute left-4 top-4 text-neutral-400 hover:text-primary-400 text-xs">← 뒤로</button>

      {/* 계정 섹션 */}
      <div className="w-full max-w-xl flex flex-col gap-2 mb-2 mt-8">
        <h2 className="text-base font-semibold mb-2">계정</h2>
        <div className="flex items-center gap-4">
          {personCircle}
          <div className="flex flex-col flex-1">
            <div className="text-xs font-normal mb-0.5">{user.username}</div>
            <div className="text-neutral-400 text-xs">{user.email}</div>
            <div className="text-neutral-400 text-xs">{user.affiliation || '소속 없음'}</div>
          </div>
          <div className="flex flex-col gap-2">
            {/* <button className="px-3 py-1.5 rounded border border-primary-600 text-primary-400 hover:bg-primary-900/30 text-xs">사용자 이름 변경</button> */}
            {/* <button className="px-3 py-1.5 rounded border border-primary-600 text-primary-400 hover:bg-primary-900/30 text-xs">소속 변경</button> */}
          </div>
        </div>
      </div>
      <div className="w-full max-w-xl border-t border-neutral-800 my-4" />

      {/* 구독 섹션 */}
      <div className="w-full max-w-xl flex flex-col gap-2 mb-2">
        <div className="text-base font-semibold mb-1">구독</div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-900">
              {user.is_membership ? 'Pro' : 'Basic'}
            </span>
            {user.is_membership && (
              <span className="px-2 py-1 bg-primary-100 text-primary-600 text-xs rounded-full">
                구독 중
              </span>
            )}
          </div>
          <button 
            onClick={() => navigate('/plan')} 
            className="px-3 py-1.5 rounded bg-primary-500 text-white font-medium hover:bg-primary-600 text-xs"
          >
            {user.is_membership ? '플랜 관리' : '플랜 업그레이드'}
          </button>
        </div>
        
        {/* 토큰 섹션 */}
        <div className="grid grid-cols-2 gap-x-2 gap-y-3 items-center text-xs mt-3">
          <div className="text-gray-900">토큰</div>
          <div className="flex justify-end">
            <button 
              onClick={handleTokenUsage}
              className="px-3 py-1.5 rounded border border-neutral-700 text-gray-900 hover:bg-neutral-800 text-xs"
            >
              사용량 조회
            </button>
          </div>
        </div>
      </div>
      <div className="w-full max-w-xl border-t border-neutral-800 my-4" />

      {/* 시스템 섹션 */}
      <div className="w-full max-w-xl flex flex-col gap-2 mb-2">
        <div className="text-base font-semibold mb-1">시스템</div>
        <div className="grid grid-cols-2 gap-x-2 gap-y-3 items-center text-xs">
          <div className="text-gray-900">기록</div>
          <div className="flex justify-end">
            <button 
              onClick={handleHistoryView}
              className="px-3 py-1.5 rounded border border-neutral-700 text-gray-900 hover:bg-neutral-800 text-xs"
            >
              조회하기
            </button>
          </div>

          <div className="text-gray-900">지원</div>
          <div className="flex justify-end"><button onClick={() => setShowContactModal(true)} className="px-3 py-1.5 rounded border border-neutral-700 text-gray-900 hover:bg-neutral-800 text-xs">연락하기</button></div>

          <div className="text-gray-900">당신은 다음으로 로그인했습니다: <span className="text-primary-400">{user.username}</span></div>
          <div className="flex justify-end"><button onClick={handleLogout} className="px-3 py-1.5 rounded border border-neutral-700 text-gray-900 hover:bg-neutral-800 text-xs">로그아웃</button></div>

          <div className="text-red-400">계정 삭제</div>
          <div className="flex justify-end"><button onClick={() => setShowDeleteModal(true)} className="px-3 py-1.5 rounded border border-red-500 text-red-400 hover:bg-red-900/30 text-xs">더 알아보기</button></div>
        </div>
      </div>

      {/* 토큰 사용량 모달 */}
      {showTokenModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">토큰 사용량</h3>
              <button
                onClick={() => setShowTokenModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            {/* 조회 옵션 */}
            <div className="mb-4">
              <div className="flex gap-4 mb-3">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="viewType"
                    value="service"
                    checked={viewType === 'service'}
                    onChange={(e) => setViewType(e.target.value)}
                    className="mr-2"
                  />
                  유형별 조회
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="viewType"
                    value="period"
                    checked={viewType === 'period'}
                    onChange={(e) => setViewType(e.target.value)}
                    className="mr-2"
                  />
                  기간별 조회
                </label>
              </div>

              {viewType === 'service' && (
                <div className="flex gap-2 items-center">
                  <select
                    value={selectedService}
                    onChange={(e) => setSelectedService(e.target.value)}
                    className="border border-gray-300 rounded px-3 py-1 text-sm"
                  >
                    <option value="">전체</option>
                    <option value="query_summary">검색 분석</option>
                    <option value="analyze_reports">보고서 분석</option>
                    <option value="chat_report">보고서 채팅</option>
                    <option value="write_chat">보고서 작성</option>
                  </select>
                  <button
                    onClick={handleFilterChange}
                    className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                  >
                    조회
                  </button>
                </div>
              )}

              {viewType === 'period' && (
                <div className="flex gap-2 items-center">
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="border border-gray-300 rounded px-3 py-1 text-sm"
                  />
                  <span>~</span>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="border border-gray-300 rounded px-3 py-1 text-sm"
                  />
                  <button
                    onClick={handleFilterChange}
                    className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                  >
                    조회
                  </button>
                </div>
              )}
            </div>

            {/* 로딩 상태 */}
            {tokenLoading && (
              <div className="text-center py-8">
                <div className="text-gray-500">로딩 중...</div>
              </div>
            )}

            {/* 토큰 사용량 데이터 */}
            {!tokenLoading && tokenUsage && (
              <div className="space-y-4">
                {/* 전체 요약 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">전체 요약</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>총 요청 수: <span className="font-medium">{tokenUsage.summary.total_requests.toLocaleString()}회</span></div>
                    <div>총 토큰 수: <span className="font-medium">{tokenUsage.summary.total_tokens.toLocaleString()}개</span></div>
                    <div>요청 토큰: <span className="font-medium">{tokenUsage.summary.total_request_tokens.toLocaleString()}개</span></div>
                    <div>응답 토큰: <span className="font-medium">{tokenUsage.summary.total_response_tokens.toLocaleString()}개</span></div>
                  </div>
                </div>

                {/* 서비스별 통계 */}
                {Object.keys(tokenUsage.by_service).length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">서비스별 사용량</h4>
                    <div className="space-y-2">
                      {Object.entries(tokenUsage.by_service).map(([serviceName, stats]) => (
                        <div key={serviceName} className="border border-gray-200 p-3 rounded">
                          <div className="font-medium text-sm mb-1">{getServiceDisplayName(serviceName)}</div>
                          <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                            <div>요청: {stats.requests.toLocaleString()}회</div>
                            <div>총 토큰: {stats.total_tokens.toLocaleString()}개</div>
                            <div>요청 토큰: {stats.request_tokens.toLocaleString()}개</div>
                            <div>응답 토큰: {stats.response_tokens.toLocaleString()}개</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 최근 로그 (최대 10개) */}
                {tokenUsage.logs.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">최근 사용 기록</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {tokenUsage.logs
                        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                        .slice(0, 10)
                        .map((log, index) => (
                          <div key={index} className="border border-gray-200 p-2 rounded text-xs">
                            <div className="flex justify-between items-start mb-1">
                              <span className="font-medium">{getServiceDisplayName(log.service_name)}</span>
                              <span className="text-gray-500">
                                {new Date(log.timestamp).toLocaleDateString('ko-KR', {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </span>
                            </div>
                            <div className="text-gray-600">
                              토큰: {log.total_token_count?.toLocaleString() || 0}개 
                              (요청: {log.request_token_count?.toLocaleString() || 0}, 
                              응답: {log.response_token_count?.toLocaleString() || 0})
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 기록 조회 모달 */}
      {showHistoryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">검색/채팅 기록</h3>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            {/* 필터 옵션 */}
            <div className="mb-4">
              <div className="flex gap-4 items-center">
                <span className="text-sm font-medium">조회 유형:</span>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="historyType"
                    value="all"
                    checked={historyType === 'all'}
                    onChange={(e) => setHistoryType(e.target.value)}
                    className="mr-2"
                  />
                  전체
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="historyType"
                    value="search"
                    checked={historyType === 'search'}
                    onChange={(e) => setHistoryType(e.target.value)}
                    className="mr-2"
                  />
                  검색 기록
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="historyType"
                    value="chat"
                    checked={historyType === 'chat'}
                    onChange={(e) => setHistoryType(e.target.value)}
                    className="mr-2"
                  />
                  채팅 기록
                </label>
                <button
                  onClick={handleHistoryFilterChange}
                  className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                >
                  조회
                </button>
              </div>
            </div>

            {/* 로딩 상태 */}
            {historyLoading && (
              <div className="text-center py-8">
                <div className="text-gray-500">로딩 중...</div>
              </div>
            )}

            {/* 기록 데이터 */}
            {!historyLoading && userHistory && (
              <div className="space-y-4">
                {/* 요약 */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">요약</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>총 기록: <span className="font-medium">{userHistory.summary.total_records.toLocaleString()}개</span></div>
                    <div>검색 기록: <span className="font-medium">{userHistory.summary.search_count.toLocaleString()}개</span></div>
                    <div>채팅 기록: <span className="font-medium">{userHistory.summary.chat_count.toLocaleString()}개</span></div>
                  </div>
                </div>

                {/* 기록 목록 */}
                {userHistory.history.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-2">기록 목록</h4>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {userHistory.history
                        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                        .map((log, index) => (
                          <div key={index} className="border border-gray-200 p-3 rounded">
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  ['chat_report', 'write_chat'].includes(log.service_name)
                                    ? 'bg-green-100 text-green-600' 
                                    : 'bg-blue-100 text-blue-600'
                                }`}>
                                  {getServiceDisplayName(log.service_name)}
                                </span>
                                <span className="text-gray-500 text-xs">
                                  {new Date(log.timestamp).toLocaleDateString('ko-KR', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                </span>
                              </div>
                              <span className="text-xs text-gray-500">
                                토큰: {log.total_token_count?.toLocaleString() || 0}개
                              </span>
                            </div>
                            <div className="text-sm text-gray-700 bg-gray-50 p-2 rounded">
                              <div className="font-medium mb-1">프롬프트:</div>
                              <div className="text-xs break-words">
                                {log.request_prompt?.length > 200 
                                  ? `${log.request_prompt.substring(0, 200)}...` 
                                  : log.request_prompt || '프롬프트 없음'}
                              </div>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {userHistory.history.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    조회된 기록이 없습니다.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 연락하기 모달 */}
      {showContactModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-4 text-center">문의하기</h3>
            <p className="text-sm text-gray-600 mb-6 text-center">
              legojeon@kaist.ac.kr로 문의주세요
            </p>
            <div className="flex justify-center">
              <button
                onClick={() => setShowContactModal(false)}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition"
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 계정 삭제 모달 */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-4 text-center">계정을 삭제하시겠습니까?</h3>
            <p className="text-sm text-gray-600 mb-6 text-center">
              이 작업은 되돌릴 수 없습니다. 모든 데이터가 영구적으로 삭제됩니다.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={deleteLoading}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
              >
                취소
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteLoading}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50"
              >
                {deleteLoading ? '삭제 중...' : '계정 삭제'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProfilePage; 
