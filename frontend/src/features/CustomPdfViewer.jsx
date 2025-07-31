import React, { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

// PDF.js Worker 설정 (버전 5.3.93에 맞춤)
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';

function PdfPage({ pdf, pageNumber, scale }) {
  const canvasRef = useRef(null);
  const renderTaskRef = useRef(null);
  const [isRendering, setIsRendering] = useState(false);

  useEffect(() => {
    const renderPage = async () => {
      if (!pdf || !canvasRef.current) return;
      
      setIsRendering(true);
      
      // 이전 렌더링 작업이 있다면 취소
      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel();
        } catch (e) {
          // 이미 취소된 경우 무시
        }
      }

      try {
        const page = await pdf.getPage(pageNumber);
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        
        // 캔버스 컨텍스트를 새로 가져오기
        const context = canvas.getContext('2d');
        
        // 캔버스 크기 설정
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        // 캔버스 초기화
        context.clearRect(0, 0, canvas.width, canvas.height);
        
        // 렌더링 작업 시작
        renderTaskRef.current = page.render({ 
          canvasContext: context, 
          viewport 
        });
        
        await renderTaskRef.current.promise;
        setIsRendering(false);
      } catch (error) {
        setIsRendering(false);
        // 취소된 작업은 무시
        if (error.name !== 'RenderingCancelled' && error.message !== 'Rendering cancelled') {
          console.error('PDF 페이지 렌더링 오류:', error);
        }
      }
    };

    // 약간의 지연을 두어 이전 작업이 완전히 정리되도록 함
    const timeoutId = setTimeout(renderPage, 50);
    
    return () => {
      clearTimeout(timeoutId);
      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel();
        } catch (e) {
          // 이미 취소된 경우 무시
        }
      }
    };
  }, [pdf, pageNumber, scale]);

  return (
    <canvas 
      ref={canvasRef} 
      style={{ 
        background: 'white', 
        borderRadius: '1rem', 
        margin: '0 auto', 
        boxShadow: '0 2px 8px #eee',
        opacity: isRendering ? 0.5 : 1,
        transition: 'opacity 0.2s'
      }} 
    />
  );
}

function CustomPdfViewer({ url, height = 'calc(100%)', isSummary, onToggleSummary }) {
  const [pdf, setPdf] = useState(null);
  const [numPages, setNumPages] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [currentPage, setCurrentPage] = useState(1);
  const [loadError, setLoadError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const loadPdf = async () => {
      setLoadError(false);
      setErrorMessage('');
      
      // URL이 null이거나 빈 문자열인 경우 처리하지 않음
      if (!url) {
        setPdf(null);
        setNumPages(0);
        setLoadError(true);
        setErrorMessage('보고서 파일이 존재하지 않습니다');
        return;
      }
      
      try {
        const loadingTask = pdfjsLib.getDocument(url);
        const loadedPdf = await loadingTask.promise;
        setPdf(loadedPdf);
        setNumPages(loadedPdf.numPages);
        setCurrentPage(1); // PDF 로드 시 첫 페이지로 리셋
      } catch (error) {
        // HWP 파일인지 확인 (URL에서 파일 확장자 확인)
        const isHwpFile = url.toLowerCase().includes('.hwp') || 
                         (error.message && error.message.includes('Invalid PDF structure'));
        
        if (isHwpFile) {
          setErrorMessage('보고서 파일 형식이 맞지 않습니다');
        } else {
          setErrorMessage('보고서 파일이 존재하지 않습니다');
        }
        
        setPdf(null);
        setNumPages(0);
        setLoadError(true);
      }
    };
    loadPdf();
  }, [url]);

  // 페이지 이동 함수들
  const goToPreviousPage = () => {
    setCurrentPage(prev => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setCurrentPage(prev => Math.min(numPages, prev + 1));
  };

  // 현재 페이지만 렌더링
  const renderCurrentPage = () => {
    if (!pdf) return null;
    return (
      <PdfPage 
        key={`${currentPage}-${scale}`} // 고유한 키로 컴포넌트 새로 생성
        pdf={pdf} 
        pageNumber={currentPage} 
        scale={scale} 
      />
    );
  };

  return (
    <div className="border-2 border-primary-700 bg-white shadow-lg overflow-hidden flex flex-col" style={{ width: 700, height, maxWidth: '100%' }}>
      {/* PDF 렌더링 영역 (세로 스크롤) */}
      <div className="flex-1 w-full bg-white overflow-auto" style={{ minHeight: 0, position: 'relative' }}>
        <div className="flex flex-col items-center gap-4 py-4 h-full justify-center" style={{height: '100%'}}>
          {loadError ? (
            <div className="flex items-center justify-center h-full w-full" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}>
              <p className="text-black text-base font-semibold" style={{ textAlign: 'center' }}>
                {errorMessage}
              </p>
            </div>
          ) : (
            renderCurrentPage()
          )}
        </div>
      </div>
      {/* 파란색 툴바 (하단) - 항상 렌더링 */}
      <div className="w-full flex items-center justify-between px-4 py-2 bg-primary-600" style={{ height: 44, flexShrink: 0, zIndex: 1 }}>
        {/* 왼쪽: 확대/축소 */}
        <div className="flex items-center gap-2">
          <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))} className="text-white px-2 py-1 rounded" disabled={loadError}>-</button>
          <span className="text-white text-xs">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.min(2.5, s + 0.1))} className="text-white px-2 py-1 rounded" disabled={loadError}>+</button>
        </div>
        
        {/* 중앙: 페이지 이동 */}
        <div className="flex items-center gap-2">
          <button 
            onClick={goToPreviousPage} 
            disabled={currentPage <= 1 || loadError}
            className="text-white px-2 py-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ‹
          </button>
          <span className="text-white text-xs px-2">
            {currentPage} / {numPages}
          </span>
          <button 
            onClick={goToNextPage} 
            disabled={currentPage >= numPages || loadError}
            className="text-white px-2 py-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ›
          </button>
        </div>
        
        {/* 오른쪽: 요약/상세 버튼 - 항상 활성화 */}
        <button
          onClick={onToggleSummary}
          className="text-white bg-primary-700 hover:bg-primary-800 px-4 py-1 rounded-lg text-sm font-medium transition-colors border border-primary-700"
        >
          {isSummary ? '전체보고서 보기' : '요약보고서 보기'}
        </button>
      </div>
    </div>
  );
}

export default CustomPdfViewer; 