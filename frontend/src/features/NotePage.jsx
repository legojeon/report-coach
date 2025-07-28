import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getUserNotes, deactivateNote } from '../services/api';

function NotePage() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNote, setSelectedNote] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [filterType, setFilterType] = useState('all'); // 'all', 'chat_report', 'write_report'
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsLoggedIn(!!token);
    
    // 로그인하지 않은 경우 로그인 페이지로 리다이렉트
    if (!token) {
      navigate('/login');
      return;
    }

    // 노트 데이터 로드
    const loadNotes = async () => {
      try {
        setLoading(true);
        const notesData = await getUserNotes(token);
        setNotes(notesData);
        setError(null);
      } catch (err) {
        console.error('노트 로드 실패:', err);
        setError('노트를 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };

    loadNotes();
  }, [navigate]);

  const handleMembershipClick = () => {
    navigate('/plan');
  };

  const handleWriteClick = () => {
    navigate('/write');
  };

  const handleMyNotesClick = () => {
    navigate('/notes');
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getServiceDisplayName = (serviceName) => {
    switch (serviceName) {
      case 'chat_report':
        return '대화 요약';
      case 'write_report':
        return '탐구 보고서';
      default:
        return serviceName;
    }
  };

  const handleNoteClick = (note) => {
    setSelectedNote(note);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedNote(null);
  };

  const handleContinueChat = () => {
    if (selectedNote) {
      if (selectedNote.service_name === 'write_report') {
        // WritePage로 이동하면서 노트 데이터(id 포함) 전달
        const noteData = {
          id: selectedNote.id, // 반드시 id 포함
          title: selectedNote.title,
          chat_history: selectedNote.chat_history,
          chat_summary: selectedNote.chat_summary
        };
        navigate('/write', { state: { noteData } });
      } else {
        // 채팅 페이지로 이동하면서 보고서 번호 전달
        navigate(`/chat?report=${selectedNote.nttsn}`);
      }
      setShowModal(false);
      setSelectedNote(null);
    }
  };

  const handleDeleteNote = async () => {
    if (!selectedNote) return;
    const token = localStorage.getItem('token');
    try {
      await deactivateNote(token, selectedNote.id);
      setShowModal(false);
      setSelectedNote(null);
      // 노트 목록 새로고침
      const notesData = await getUserNotes(token);
      setNotes(notesData);
    } catch (err) {
      alert('노트 삭제에 실패했습니다.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 
                onClick={() => navigate('/')}
                className="text-2xl font-bold text-primary-600 cursor-pointer hover:text-primary-700 transition-colors"
              >
                ReportCoach
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <button onClick={handleMembershipClick} className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                멤버쉽
              </button>
              {isLoggedIn ? (
                <>
                  <span onClick={() => navigate('/profile')} className="cursor-pointer">
                    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" fill="#1D4ED8" viewBox="0 0 16 16" className="bg-blue-100 rounded-full p-1">
                      <path d="M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0" />
                      <path fillRule="evenodd" d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8m8-7a7 7 0 0 0-5.468 11.37C3.242 11.226 4.805 10 8 10s4.757 1.225 5.468 2.37A7 7 0 0 0 8 1" />
                    </svg>
                  </span>
                  <button onClick={handleMyNotesClick} className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium border border-gray-300 hover:border-gray-400 transition-colors">
                    내 노트
                  </button>
                </>
              ) : (
                <Link to="/login" className="text-primary-600 hover:text-primary-700 px-3 py-2 rounded-md text-sm font-medium border border-primary-600 hover:bg-primary-50 transition-colors">
                  로그인
                </Link>
              )}
              <button 
                onClick={handleWriteClick}
                className="bg-primary-600 hover:bg-primary-700 text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
              >
                작성하기
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">내 노트</h2>
              <p className="text-gray-600">저장된 노트들을 확인해보세요</p>
            </div>
            <div className="flex items-center space-x-2">
              <label htmlFor="filter" className="text-sm font-medium text-gray-700">
              </label>
              <select
                id="filter"
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">모두 보기</option>
                <option value="chat_report">대화 요약</option>
                <option value="write_report">탐구 보고서</option>
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center items-center min-h-[400px]">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <div className="text-red-500 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">오류가 발생했습니다</h3>
            <p className="text-gray-500">{error}</p>
          </div>
        ) : notes.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">현재 저장된 노트가 없습니다</h3>
            <p className="text-gray-500">노트를 작성해보세요!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {notes
              .filter(note => note.is_active !== false)
              .filter(note => {
                if (filterType === 'all') return true;
                return note.service_name === filterType;
              })
              .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
              .map((note) => (
                <div
                  key={note.id}
                  onClick={() => handleNoteClick(note)}
                  className={`p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer transform hover:-translate-y-1 transition-transform ${
                    note.service_name === 'write_report' 
                      ? 'bg-blue-100 border-l-4 border-blue-400' 
                      : 'bg-yellow-100 border-l-4 border-yellow-400'
                  }`}
                  style={{
                    background: note.service_name === 'write_report' 
                      ? 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)'
                      : 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                  }}
                >
                  <div className="mb-4">
                    <h3 className="text-lg font-bold text-gray-800 mb-2 line-clamp-2">
                      {note.title || `노트 ${note.nttsn}`}
                    </h3>
                    <div className="flex items-center justify-between">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        note.service_name === 'write_report'
                          ? 'bg-blue-200 text-blue-800'
                          : 'bg-yellow-200 text-yellow-800'
                      }`}>
                        {getServiceDisplayName(note.service_name)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatDate(note.updated_at)}
                      </span>
                    </div>
                  </div>
                  
                  {note.chat_summary && (
                    <div className="text-sm text-gray-700 line-clamp-3">
                      {/* 마크다운/HTML 태그 제거 후 텍스트만 표시 */}
                      {note.service_name === 'write_report'
                        ? (note.chat_summary.replace(/<[^>]+>/g, '').replace(/[#*_`>\-\[\]()~]/g, '').replace(/\n/g, ' '))
                        : note.chat_summary}
                    </div>
                  )}
                  
                  <div className={`mt-4 pt-3 border-t ${
                    note.service_name === 'write_report'
                      ? 'border-blue-300'
                      : 'border-yellow-300'
                  }`}>
                    <div className="flex justify-between items-center text-xs text-gray-600">
                      <span>보고서 #{note.nttsn}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 포스트잇 모달 */}
        {showModal && selectedNote && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div 
              className={`p-8 rounded-lg shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden ${
                selectedNote.service_name === 'write_report'
                  ? 'bg-blue-100 border-l-4 border-blue-400'
                  : 'bg-yellow-100 border-l-4 border-yellow-400'
              }`}
              style={{
                background: selectedNote.service_name === 'write_report'
                  ? 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)'
                  : 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
              }}
            >
              {/* 모달 헤더 */}
              <div className="flex justify-between items-start mb-6">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-800 mb-2">
                    {selectedNote.title || `노트 ${selectedNote.nttsn}`}
                  </h2>
                  <div className="flex items-center justify-between">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                      selectedNote.service_name === 'write_report'
                        ? 'bg-blue-200 text-blue-800'
                        : 'bg-yellow-200 text-yellow-800'
                    }`}>
                      {getServiceDisplayName(selectedNote.service_name)}
                    </span>
                    <span className="text-sm text-gray-500">
                      {formatDate(selectedNote.updated_at)}
                    </span>
                  </div>
                </div>
                {/* 쓰레기통 아이콘 버튼 */}
                <button
                  onClick={handleCloseModal}
                  className="ml-2 text-gray-500 hover:text-gray-700 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* 모달 내용 */}
              <div className="flex-1 overflow-y-auto max-h-[50vh] mb-6">
                {selectedNote.chat_summary ? (
                  <div className={`bg-white bg-opacity-50 rounded-lg p-4 max-h-100 overflow-y-auto ${
                    selectedNote.service_name === 'write_report'
                      ? 'border border-blue-300'
                      : 'border border-yellow-300'
                  }`}>
                    <h3 className="text-lg font-semibold text-gray-800 mb-3">
                      {selectedNote.service_name === 'write_report' ? '보고서 내용' : '대화 요약'}
                    </h3>
                    <div className="text-gray-700 leading-relaxed">
                      {selectedNote.service_name === 'write_report' ? (
                        // HTML/마크다운 원본을 그대로 렌더링
                        <div dangerouslySetInnerHTML={{ __html: selectedNote.chat_summary }} />
                      ) : (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({node, ...props}) => <h1 className="text-lg font-bold mb-2 text-gray-900" {...props} />, 
                            h2: ({node, ...props}) => <h2 className="text-base font-semibold mb-2 text-gray-900" {...props} />, 
                            h3: ({node, ...props}) => <h3 className="text-sm font-semibold mb-1 text-gray-900" {...props} />, 
                            p: ({node, ...props}) => <p className="mb-2 leading-relaxed" {...props} />, 
                            ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 space-y-1" {...props} />, 
                            ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 space-y-1" {...props} />, 
                            li: ({node, ...props}) => <li className="text-sm" {...props} />, 
                            strong: ({node, ...props}) => <strong className="font-semibold" {...props} />, 
                            em: ({node, ...props}) => <em className="italic" {...props} />, 
                            code: ({node, inline, ...props}) => 
                              inline ? (
                                <code className="bg-gray-200 px-1 py-0.5 rounded text-xs font-mono" {...props} />
                              ) : (
                                <code className="block bg-gray-200 p-2 rounded text-xs font-mono overflow-x-auto" {...props} />
                              ), 
                            pre: ({node, ...props}) => <pre className="bg-gray-200 p-2 rounded text-xs font-mono overflow-x-auto mb-2" {...props} />, 
                            blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-primary-300 pl-3 italic text-gray-700 mb-2" {...props} />,
                          }}
                        >
                          {selectedNote.chat_summary}
                        </ReactMarkdown>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    <svg className="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p>요약 내용이 없습니다.</p>
                  </div>
                )}
              </div>

              {/* 모달 하단 정보 */}
              <div className={`border-t pt-4 ${
                selectedNote.service_name === 'write_report'
                  ? 'border-blue-300'
                  : 'border-yellow-300'
              }`}>
                <div className="flex justify-between items-center text-sm text-gray-600 mb-4">
                  <span>보고서 #{selectedNote.nttsn}</span>
                  {/* 쓰레기통 아이콘 버튼 */}
                  <button
                    className="ml-2 text-gray-400 hover:text-red-500 transition-colors"
                    title="노트 삭제"
                    onClick={handleDeleteNote}
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 7h12M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3m2 0v12a2 2 0 01-2 2H8a2 2 0 01-2-2V7h12z" />
                    </svg>
                  </button>
                </div>
                
                {/* 대화 이어가기 버튼 */}
                <button
                  onClick={handleContinueChat}
                  className="w-full bg-primary-600 hover:bg-primary-700 text-white py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  {selectedNote.service_name === 'write_report' ? '작성 이어가기' : '대화 이어가기'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  export default NotePage; 