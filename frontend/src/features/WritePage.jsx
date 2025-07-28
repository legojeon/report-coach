import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';  // 수학 수식 지원
import rehypeKatex from 'rehype-katex';  // 수학 수식 렌더링
import 'katex/dist/katex.min.css';  // KaTeX 스타일
import TiptapEditor from '../components/TiptapEditor';
import { chatWithWrite, cleanupWriteSession, getWriteChatHistory, updateOrCreateNote } from '../services/api';
import { getMe } from '../services/auth';

function WritePage() {
  const [content, setContent] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const chatEndRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }
    setIsLoggedIn(true);
    // 사용자 정보 가져오기
    const fetchUser = async () => {
      try {
        const data = await getMe(token);
        setUser(data);
      } catch (err) {
        setUser(null);
      }
    };
    fetchUser();
  }, [navigate]);

  // 자동 저장 기능
  useEffect(() => {
    const interval = setInterval(() => {
      if (content.trim()) {
        localStorage.setItem('writePage_draft', content);
      }
    }, 30000); // 30초마다 자동 저장

    return () => clearInterval(interval);
  }, [content]);

  // 컴포넌트 마운트 시 저장된 초안 불러오기 또는 노트 데이터 복구
  useEffect(() => {
    // 노트 데이터가 전달된 경우 (작성 이어가기)
    if (location.state?.noteData) {
      const { noteData } = location.state;
      
      // 텍스트 영역에 chat_summary 내용 설정
      if (noteData.chat_summary) {
        setContent(noteData.chat_summary);
      } else {
      }
      
      // 채팅 히스토리 복구
      if (noteData.chat_history) {
        try {
          const history = typeof noteData.chat_history === 'string' 
            ? JSON.parse(noteData.chat_history) 
            : noteData.chat_history;
          
          const convertedMessages = history.map((msg, index) => ({
            id: Date.now() + index,
            type: msg.role === 'assistant' ? 'ai' : 'user',
            content: msg.content,
            timestamp: new Date()
          }));
          
          setChatMessages(convertedMessages);
        } catch (error) {
          console.error('채팅 히스토리 파싱 오류:', error);
        }
      }
      
      // 초안 삭제 (노트 데이터로 복구했으므로)
      localStorage.removeItem('writePage_draft');
    } else {
      // 일반적인 경우 - 저장된 초안 불러오기
      const savedDraft = localStorage.getItem('writePage_draft');
      if (savedDraft) {
        setContent(savedDraft);
      }
    }
  }, [location.state]);

  // 페이지를 떠날 때 히스토리 정리
  useEffect(() => {
    const handleBeforeUnload = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          await cleanupWriteSession(token);
        } catch (error) {
          console.error('히스토리 정리 중 오류:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // 컴포넌트 언마운트 시에도 히스토리 정리
      handleBeforeUnload();
    };
  }, []);

  // 채팅 스크롤 자동 이동
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setChatMessages(prev => [...prev, userMessage]);
    const currentMessage = inputMessage;
    setInputMessage('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('로그인이 필요합니다.');
      }

      // 현재 텍스트 영역의 content를 user_report로 전송
      const response = await chatWithWrite(token, currentMessage, content);
      
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: response.response,
        timestamp: new Date()
      };
      
      setChatMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('채팅 오류:', error);
      
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: '죄송합니다. 답변 생성 중 오류가 발생했습니다. 다시 시도해주세요.',
        timestamp: new Date()
      };
      
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleMembershipClick = () => {
    navigate('/plan');
  };

  const handleMyNotesClick = () => {
    navigate('/notes');
  };

  const handleSave = async () => {
    if (!content.trim()) {
      alert('저장할 내용이 없습니다.');
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      alert('로그인이 필요합니다.');
      return;
    }

    setIsSaving(true);

    try {
      // HTML 내용을 텍스트로 변환
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = content;
      const textContent = tempDiv.textContent || tempDiv.innerText || '';
      
      // 첫 번째 의미있는 텍스트를 title로 사용
      const lines = textContent.split('\n').filter(line => line.trim() !== '');
      let title = '무제 보고서';
      
      if (lines.length > 0) {
        // 첫 번째 의미있는 줄을 찾기
        for (let line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine && trimmedLine.length > 0) {
            // 제목이 너무 길면 잘라내기 (50자 제한)
            title = trimmedLine.length > 20 ? trimmedLine.substring(0, 50) + '...' : trimmedLine;
            break;
          }
        }
      }
      
      // 채팅 히스토리를 서버 형식으로 변환
      const chatHistory = chatMessages.map(msg => ({
        role: msg.type === 'ai' ? 'assistant' : 'user',
        content: msg.content
      }));

      // 노트 데이터 준비
      const noteData = {
        nttsn: null,  // null로 설정
        title: title,
        service_name: 'write_report',
        chat_history: chatHistory,
        chat_summary: content  // 마크다운/HTML 원본 그대로 저장
      };
      if (location.state?.noteData?.id) {
        noteData.id = location.state.noteData.id;
      }
      // 노트 저장
      const savedNote = await updateOrCreateNote(token, noteData);
      
      if (savedNote) {
        // 성공 모달 표시
        setShowSaveModal(true);
        setTimeout(() => setShowSaveModal(false), 1800);
        // 저장 후 초안 삭제
        localStorage.removeItem('writePage_draft');
      } else {
        alert('노트 저장에 실패했습니다.');
      }
    } catch (error) {
      console.error('노트 저장 오류:', error);
      alert('노트 저장 중 오류가 발생했습니다.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 저장 성공 모달 */}
      {showSaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
          <div className="bg-white rounded-xl shadow-lg px-8 py-6 flex flex-col items-center animate-fade-in">
            <svg className="w-12 h-12 text-green-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <div className="text-lg font-semibold text-gray-800 mb-1">노트 저장 완료</div>
            <div className="text-gray-500 text-sm">채팅이 노트에 저장되었습니다!</div>
          </div>
        </div>
      )}
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
                onClick={handleSave}
                disabled={isSaving}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isSaving 
                    ? 'bg-gray-400 text-white cursor-not-allowed' 
                    : 'bg-primary-600 hover:bg-primary-700 text-white'
                }`}
              >
                {isSaving ? '저장 중...' : '저장하기'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <div className="flex h-[calc(100vh-64px)]">
        {/* 왼쪽 채팅 영역 */}
        <div className="w-1/2 bg-white border-r border-gray-200 flex flex-col">
          <div className="flex-1 overflow-y-auto p-4">
            {chatMessages.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <div className="text-lg font-medium mb-2">AI 어시스턴트와 대화하세요</div>
                <div className="text-sm">리포트 작성에 도움이 필요한 내용을 물어보세요</div>
              </div>
            ) : (
              <div className="space-y-4">
                {chatMessages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-2 ${
                        message.type === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      {message.type === 'user' ? (
                        <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                      ) : (
                        <div className="text-sm prose prose-sm max-w-none">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm, remarkMath]}
                            rehypePlugins={[rehypeKatex]}
                            components={{
                              h1: ({node, ...props}) => <h1 className="text-lg font-bold mb-2 text-gray-900" {...props} />,
                              h2: ({node, ...props}) => <h2 className="text-base font-semibold mb-2 text-gray-900" {...props} />,
                              h3: ({node, ...props}) => <h3 className="text-sm font-semibold mb-1 text-gray-900" {...props} />,
                              h4: ({node, ...props}) => <h4 className="text-sm font-semibold mb-1 text-gray-900" {...props} />,
                              h5: ({node, ...props}) => <h5 className="text-sm font-semibold mb-1 text-gray-900" {...props} />,
                              h6: ({node, ...props}) => <h6 className="text-sm font-semibold mb-1 text-gray-900" {...props} />,
                              p: ({node, ...props}) => <p className="mb-2 leading-relaxed text-gray-900" {...props} />,
                              ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 space-y-1 text-gray-900" {...props} />,
                              ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 space-y-1 text-gray-900" {...props} />,
                              li: ({node, ...props}) => <li className="text-sm text-gray-900" {...props} />,
                              strong: ({node, ...props}) => <strong className="font-semibold text-gray-900" {...props} />,
                              em: ({node, ...props}) => <em className="italic text-gray-900" {...props} />,
                              code: ({node, inline, className, children, ...props}) => {
                                const match = /language-(\w+)/.exec(className || '');
                                return !inline && match ? (
                                  <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto mb-2">
                                    <code className={`text-xs font-mono ${className}`} {...props}>
                                      {children}
                                    </code>
                                  </pre>
                                ) : (
                                  <code className="bg-gray-200 px-1 py-0.5 rounded text-xs font-mono text-gray-800" {...props}>
                                    {children}
                                  </code>
                                );
                              },
                              pre: ({node, ...props}) => <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto mb-2 text-xs font-mono" {...props} />,
                              blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-primary-300 pl-3 italic text-gray-700 mb-2 bg-gray-50 py-2" {...props} />,
                              table: ({node, ...props}) => <table className="min-w-full border border-gray-300 mb-2" {...props} />,
                              thead: ({node, ...props}) => <thead className="bg-gray-100" {...props} />,
                              tbody: ({node, ...props}) => <tbody {...props} />,
                              tr: ({node, ...props}) => <tr className="border-b border-gray-300" {...props} />,
                              th: ({node, ...props}) => <th className="px-3 py-2 text-left text-sm font-semibold text-gray-900" {...props} />,
                              td: ({node, ...props}) => <td className="px-3 py-2 text-sm text-gray-900" {...props} />,
                              a: ({node, ...props}) => <a className="text-primary-600 hover:text-primary-700 underline" {...props} />,
                              hr: ({node, ...props}) => <hr className="border-gray-300 my-4" {...props} />,
                              // 수학 수식 지원
                              math: ({node, inline, children, ...props}) => {
                                return inline ? (
                                  <span className="text-primary-600 font-mono" {...props}>{children}</span>
                                ) : (
                                  <div className="my-4 text-center" {...props}>{children}</div>
                                );
                              },
                              inlineMath: ({node, children, ...props}) => (
                                <span className="text-primary-600 font-mono" {...props}>{children}</span>
                              ),
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      )}
                      <div className={`text-xs mt-1 ${
                        message.type === 'user' ? 'text-primary-200' : 'text-gray-500'
                      }`}>
                        {message.timestamp.toLocaleTimeString('ko-KR', {
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 text-gray-900 rounded-lg px-4 py-2">
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                        <span className="text-sm">AI가 응답하고 있습니다...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          
          {/* 메시지 입력 영역 */}
          <div className="border-t border-gray-200 p-4">
            {user && !user.is_membership ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center w-full">
                  <p className="text-gray-600 text-sm mb-2">Pro 멤버십 회원만 AI 채팅 기능을 이용할 수 있습니다</p>
                  <button
                    onClick={() => navigate('/plan')}
                    className="px-4 py-2 rounded-md bg-primary-600 text-white font-medium hover:bg-primary-700 transition-colors text-sm"
                  >
                    Pro 멤버십 가입하기
                  </button>
                </div>
              </div>
            ) : (
              <>
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="메시지를 입력하세요... (Enter로 전송, Shift+Enter로 줄바꿈)"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  rows={4}
                  style={{ minHeight: '120px', maxHeight: '200px' }}
                />
              </>
            )}
          </div>
        </div>

        {/* 오른쪽 텍스트 영역 */}
        <div className="w-1/2 bg-white flex flex-col">
          <TiptapEditor 
            content={content}
            onChange={setContent}
          />
        </div>
      </div>
    </div>
  );
}

export default WritePage; 