import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CustomPdfViewer from './CustomPdfViewer';
import { getChatHistory, updateOrCreateNote } from '../services/api';

// 인증된 이미지 컴포넌트
const AuthenticatedImage = ({ reportNumber, className, alt }) => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const imageUrl = `${apiUrl}/search/image/${reportNumber}`;
  return (
    <img 
      src={imageUrl}
      alt={alt}
      className={className}
      onError={e => { e.target.style.display = 'none'; }}
    />
  );
}

const ChatPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [reportData, setReportData] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isSummary, setIsSummary] = useState(false);
  // PDF 파일 존재 여부 상태 추가
  const [hasReportPdf, setHasReportPdf] = useState(true);
  const [hasSummaryPdf, setHasSummaryPdf] = useState(true);
  const [messages, setMessages] = useState([]); // 채팅 메시지
  const [input, setInput] = useState(''); // 입력창
  const [isLoading, setIsLoading] = useState(false); // 로딩 상태
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userData, setUserData] = useState(null); // 사용자 데이터
  const [description, setDescription] = useState(''); // 보고서 설명
  const [isHistoryLoaded, setIsHistoryLoaded] = useState(false); // 히스토리 로드 상태
  const [showSaveModal, setShowSaveModal] = useState(false);

  useEffect(() => {
    // URL 파라미터에서 데이터 가져오기
    const dataParam = searchParams.get('data');
    const reportParam = searchParams.get('report'); // 대화 이어가기용 파라미터
    
    if (dataParam) {
      try {
        const data = JSON.parse(decodeURIComponent(dataParam));
        setReportData(data);
        // PDF URL 생성 (처음에는 전체보고서)
        updatePdfUrl(data, false);
      } catch (error) {
        console.error('데이터 파싱 오류:', error);
      }
    } else if (reportParam) {
      // 대화 이어가기: 보고서 번호로 데이터 설정
      const reportNumber = parseInt(reportParam);
      setReportData({
        number: reportNumber,
        title: `보고서 ${reportNumber}`, // 임시 제목, 나중에 실제 제목으로 업데이트
        // 기본 데이터 설정
      });
      updatePdfUrl({ number: reportNumber }, false);
      
      // 실제 보고서 제목 가져오기
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      fetch(`${apiUrl}/chat/title/${reportNumber}`)
        .then(res => res.json())
        .then(data => {
          if (data.title) {
            setReportData(prev => ({
              ...prev,
              title: data.title
            }));
          }
        })
        .catch(err => {
          console.error('보고서 제목 가져오기 실패:', err);
        });
    }
    
    setIsLoggedIn(!!localStorage.getItem('token'));
    
    // 사용자 데이터 가져오기
    const fetchUserData = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          const userResponse = await fetch(`${apiUrl}/auth/me`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (userResponse.ok) {
            const userData = await userResponse.json();
            setUserData(userData);
            console.log('사용자 is_membership:', userData.is_membership);
          }
        } catch (error) {
          console.error('사용자 데이터 가져오기 오류:', error);
        }
      }
    };

    fetchUserData();
  }, [searchParams]);

  // 채팅 히스토리 복원
  useEffect(() => {
    const loadChatHistory = async () => {
      const reportParam = searchParams.get('report');
      if (reportParam && !isHistoryLoaded) {
        try {
          const token = localStorage.getItem('token');
          const reportNumber = parseInt(reportParam);
          
          const historyData = await getChatHistory(token, reportNumber);
          console.log('채팅 히스토리 로드:', historyData);
          
          // Gemini 형식에서 일반 메시지 형식으로 변환
          const convertedMessages = historyData.history.map(msg => ({
            role: msg.role,
            text: msg.parts[0].text
          }));
          
          setMessages(convertedMessages);
          setIsHistoryLoaded(true);
          
          // 성공 메시지 추가
          setMessages(prev => [...prev, {
            role: 'assistant',
            text: '이전 대화가 복원되었습니다. 계속해서 질문해주세요!'
          }]);
          
        } catch (error) {
          console.error('채팅 히스토리 로드 실패:', error);
          setMessages([{
            role: 'assistant',
            text: '이전 대화를 불러올 수 없습니다. 새로운 대화를 시작합니다.'
          }]);
        }
      }
    };

    loadChatHistory();
  }, [searchParams, isHistoryLoaded]);

  // 페이지를 벗어날 때만 파일 삭제 (context caching 활용)
  useEffect(() => {
    const handleUnload = () => {
      // 기존 파일 삭제 대신 cleanup_session 호출
      if (userData && userData.id && reportData && reportData.number) {
        const session_id = `${userData.id}_${reportData.number}`;
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        fetch(`${apiUrl}/chat/cleanup_session?session_id=${session_id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
      }
    };

    window.addEventListener('unload', handleUnload);
    
    return () => {
      window.removeEventListener('unload', handleUnload);
    };
  }, [userData, reportData]);

  // reportData.number로 description 불러오기
  useEffect(() => {
    if (reportData && reportData.number) {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      fetch(`${apiUrl}/chat/description/${reportData.number}`)
        .then(res => res.json())
        .then(data => {
          setDescription(data.description || '');
        })
        .catch(err => {
          setDescription('');
          console.error('description 불러오기 실패:', err);
        });
    }
  }, [reportData]);

  // PDF 파일 존재 여부 확인 함수
  const checkPdfExists = async (number, summary = false) => {
    const pdfType = summary ? 'summary' : 'report';
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const url = `${apiUrl}/chat/pdf/${pdfType}/${number}`;
    try {
      const res = await fetch(url, { method: 'HEAD' });
      return res.ok;
    } catch {
      return false;
    }
  };

  // reportData 변경 시 PDF 존재 여부 확인
  useEffect(() => {
    if (reportData && reportData.number) {
      (async () => {
        const [reportExists, summaryExists] = await Promise.all([
          checkPdfExists(reportData.number, false),
          checkPdfExists(reportData.number, true)
        ]);
        setHasReportPdf(reportExists);
        setHasSummaryPdf(summaryExists);
        // 현재 상태에 맞는 PDF url 설정
        if (isSummary) {
          if (summaryExists) {
            updatePdfUrl(reportData, true);
          } else {
            setPdfUrl(null);
          }
        } else {
          if (reportExists) {
            updatePdfUrl(reportData, false);
          } else {
            setPdfUrl(null);
          }
        }
      })();
    }
  }, [reportData, isSummary]);

  // updatePdfUrl 함수는 url만 세팅
  const updatePdfUrl = (data, summary = false) => {
    const pdfType = summary ? 'summary' : 'report';
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    setPdfUrl(`${apiUrl}/chat/pdf/${pdfType}/${data.number}`);
  };

  // 요약/전체 전환
  const toggleSummary = () => {
    if (reportData) {
      const newIsSummary = !isSummary;
      setIsSummary(newIsSummary);
      // 전환 후 존재 여부에 따라 url 세팅
      if (newIsSummary) {
        if (hasSummaryPdf) {
          updatePdfUrl(reportData, true);
        } else {
          setPdfUrl(null);
        }
      } else {
        if (hasReportPdf) {
          updatePdfUrl(reportData, false);
        } else {
          setPdfUrl(null);
        }
      }
    }
  };

  // 채팅 전송 핸들러 (context caching 활용)
  const handleSend = async () => {
    if (!input.trim() || !reportData) {
      console.log('채팅 전송 조건 미충족:', { input: input.trim(), reportData: !!reportData });
      return;
    }
    
    const userMsg = { role: 'user', text: input };
    setMessages(msgs => [...msgs, userMsg]);
    const userInput = input; // 입력값 저장
    setInput('');
    setIsLoading(true);
    
    // Pro 멤버십 체크
    if (userData && !userData.is_membership) {
      setMessages(msgs => [...msgs, { 
        role: 'assistant', 
        text: '이 기능은 Pro 멤버십 회원만 이용할 수 있습니다. Pro 멤버십으로 업그레이드하여 AI 채팅 기능을 이용해보세요!' 
      }]);
      setIsLoading(false);
      return;
    }
    
    try {
      console.log('채팅 요청 전송 (context caching 활용):', { report_number: reportData.number, query: userInput });
      const token = localStorage.getItem('token');
      // session_id 생성: userData.id + reportData.number
      let session_id = undefined;
      if (userData && userData.id && reportData && reportData.number) {
        session_id = `${userData.id}_${reportData.number}`;
      }
      
      // 히스토리를 올바른 형식으로 변환
      const history = messages.map(msg => ({
        role: msg.role === "assistant" ? "model" : msg.role,
        parts: [{ text: msg.text }]
      }));
      
      const requestBody = {
        query: userInput,
        report_number: reportData.number.toString(),
        history: history,
        ...(session_id ? { session_id } : {})
      };
      
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/chat/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('채팅 요청 실패:', response.status, errorText);
        throw new Error(`채팅 요청에 실패했습니다. (${response.status})`);
      }

      const data = await response.json();
      setMessages(msgs => [...msgs, { role: 'assistant', text: data.response }]);
      
      // 사용량 메타데이터가 있으면 로그 출력
      if (data.usage_metadata) {
        console.log('채팅 사용량 메타데이터:', data.usage_metadata);
      }
    } catch (error) {
      console.error('채팅 오류:', error);
      setMessages(msgs => [...msgs, { role: 'assistant', text: '분석 중 오류가 발생했습니다.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 엔터로 전송
  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleLogoClick = () => {
    navigate('/');
  };

  const handleMembershipClick = () => {
    navigate('/plan');
  };

  const handleWriteClick = () => {
    navigate('/write');
  };

  const handleMyNotesClick = () => {
    navigate('/notes');
  };

  // 노트에 저장 버튼 클릭 핸들러
  const handleSaveToNote = async () => {
    if (!reportData || !userData) return;
    
    const token = localStorage.getItem('token');
    let session_id = undefined;
    if (userData && userData.id && reportData && reportData.number) {
      session_id = `${userData.id}_${reportData.number}`;
    }
    
    try {
      // 1. 요약 생성 요청
      // 히스토리를 올바른 형식으로 변환
      const history = messages.map(msg => ({
        role: msg.role === "assistant" ? "model" : msg.role,
        parts: [{ text: msg.text }]
      }));
      
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const summaryResponse = await fetch(`${apiUrl}/chat/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: '지금까지의 대화 정리 및 요약해줘. 핵심내용만 알려주고 앞 뒤에 요약했다는 미사여구 내용은 빼줘. 마크다운없이 텍스트만 정돈된 포맷으로 알려줘.',
          report_number: reportData.number.toString(),
          history: history,
          ...(session_id ? { session_id } : {}),
          is_hidden: true // 노트에 저장 버튼으로 요약 요청 시에만 true
        })
      });
      
      if (!summaryResponse.ok) throw new Error('요약 요청 실패');
      const summaryData = await summaryResponse.json();
      console.log('노트에 저장(요약) 결과:', summaryData);
      
      // 2. 노트에 저장 요청 (업데이트/생성)
      // 메시지를 올바른 형태로 변환
      const convertedMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.text
      }));
      
      const noteData = {
        user_id: userData.id,
        nttsn: reportData.number,
        title: reportData.title,
        service_name: 'chat_report',
        chat_history: convertedMessages, // 변환된 채팅 내역
        chat_summary: summaryData.response // 요약 결과
      };
      
      const noteResult = await updateOrCreateNote(token, noteData);
      console.log('노트 업데이트/생성 성공:', noteResult);
      
      // 성공 모달 표시
      setShowSaveModal(true);
      setTimeout(() => setShowSaveModal(false), 1800);
      
    } catch (err) {
      console.error('노트에 저장 오류:', err);
      alert('노트 저장에 실패했습니다.');
    }
  };

  return (
    <div className="h-screen bg-gray-50 overflow-hidden">
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
            {/* 좌측: 로고 */}
            <div className="flex items-center">
              <h1 
                onClick={handleLogoClick}
                className="text-2xl font-bold text-primary-600 cursor-pointer hover:text-primary-700 transition-colors"
              >
                ReportCoach
              </h1>
            </div>
            {/* 우측: 버튼들 */}
            <div className="flex items-center space-x-4">
              <button onClick={handleMembershipClick} className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                멤버쉽
              </button>
              {isLoggedIn ? (
                <>
                  <span onClick={() => navigate('/profile')} className="cursor-pointer">
                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="#1D4ED8" viewBox="0 0 16 16" className="bg-blue-100 rounded-full p-1">
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

      <div className="flex h-full">
        {/* 왼쪽: PDF 뷰어 */}
        <div className="p-4 pt-4 border-r border-gray-200 flex flex-col items-center justify-start" style={{ width: '740px' }}>
          {/* PDF 상단 툴바 */}
          {reportData && (
            <div className="w-full bg-primary-600 text-white px-4 py-2 rounded-t-lg mb-2">
              <div className="flex flex-col items-center">
                <span className="text-sm font-semibold truncate text-center max-w-full">
                  {reportData.title}
                </span>
              </div>
            </div>
          )}
          <div style={{ 
            height: 'calc(100vh - 140px)', // 기존보다 20px 더 작게
            width: '700px',
            aspectRatio: '1 / 1.414', // A4 비율
            maxWidth: '100%',
            marginBottom: '20px'
          }}>
            <CustomPdfViewer url={pdfUrl} height="calc(100vh - 140px)" isSummary={isSummary} onToggleSummary={toggleSummary} />
          </div>
        </div>
        
        {/* 오른쪽: 채팅창 스타일 패널 */}
        <div className="flex-1 bg-primary-50 flex flex-col rounded-2xl border-2 border-primary-700" style={{ margin: '20px', height: 'calc(100vh - 100px)', width: 'calc(100% - 40px)' }}>
          <div className="flex-1 p-4 overflow-y-auto">
            {/* 보고서 내용 카드 항상 맨 위 */}
            {(description || (reportData && (reportData.description || reportData.content))) && (
              <div className="space-y-4 mb-6">
                <div className="bg-white rounded-lg shadow-sm border border-primary-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">보고서 내용</h3>
                  <div className="bg-white rounded p-3">
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                      {description || reportData.description || reportData.content}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* 채팅 메시지 렌더링 */}
            <div className="space-y-4">
              {messages.map((msg, idx) => (
                <div key={idx} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
                  <div
                    className={
                      msg.role === 'user'
                        ? 'inline-block bg-primary-700 text-white rounded-lg px-4 py-3 max-w-xs lg:max-w-md border border-primary-700'
                        : 'inline-block bg-white text-gray-900 rounded-lg px-4 py-3 max-w-xs lg:max-w-md shadow-sm border border-gray-200'
                    }
                  >
                    {msg.role === 'user' ? (
                      <span className="text-sm">{msg.text}</span>
                    ) : (
                      <div className="markdown-content text-sm">
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
                                <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono" {...props} />
                              ) : (
                                <code className="block bg-gray-100 p-2 rounded text-xs font-mono overflow-x-auto" {...props} />
                              ),
                            pre: ({node, ...props}) => <pre className="bg-gray-100 p-2 rounded text-xs font-mono overflow-x-auto mb-2" {...props} />,
                            blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-primary-300 pl-3 italic text-gray-700 mb-2" {...props} />,
                          }}
                        >
                          {msg.text}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {/* 로딩 상태 표시 */}
              {isLoading && (
                <div className="text-left">
                  <div className="inline-block bg-white text-gray-900 rounded-lg px-4 py-3 max-w-xs lg:max-w-md shadow-sm border border-gray-200">
                    <div className="flex items-center space-x-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* 채팅 입력창 위에 노트에 저장 텍스트 + 다운로드 아이콘 (텍스트처럼 보이는 버튼) */}
          <div className="w-full flex justify-center">
            <button
              className="flex items-center text-primary-700 font-medium text-sm select-none bg-transparent border-none shadow-none outline-none hover:underline focus:underline cursor-pointer"
              style={{padding: 0}}
              onClick={handleSaveToNote}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} style={{marginRight: '6px'}}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" />
              </svg>
              노트에 저장
            </button>
          </div>
          {/* 채팅 입력창 */}
          <div className="w-full p-4 border-t border-primary-200 bg-primary-50 flex items-center gap-2 rounded-b-2xl" style={{ minHeight: '64px' }}>
            {userData && !userData.is_membership ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <p className="text-gray-600 text-sm mb-2">Pro 멤버십 회원만 AI 채팅 기능을 이용할 수 있습니다</p>
                  <button
                    onClick={handleMembershipClick}
                    className="px-4 py-2 rounded-md bg-primary-600 text-white font-medium hover:bg-primary-700 transition-colors text-sm"
                  >
                    Pro 멤버십 가입하기
                  </button>
                </div>
              </div>
            ) : (
              <>
                <input
                  type="text"
                  placeholder="보고서에 대해 질문..."
                  className="flex-1 px-4 py-2 rounded-md border border-primary-300 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white text-gray-900 text-sm"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleInputKeyDown}
                />
                <button
                  className="px-4 py-2 rounded-md bg-primary-500 text-white font-medium hover:bg-primary-600 transition-colors"
                  onClick={handleSend}
                >
                  전송
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage; 