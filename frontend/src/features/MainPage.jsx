import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

function MainPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem('token'))
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      // ListPage로 이동하면서 검색어를 URL 파라미터로 전달
      navigate(`/list?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  const handleMembershipClick = () => {
    navigate('/plan');
  };

  const handleLogoClick = () => {
    navigate('/');
  };

  const handleMyNotesClick = () => {
    navigate('/notes');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 
                onClick={handleLogoClick}
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
                onClick={() => navigate('/write')}
                className="bg-primary-600 hover:bg-primary-700 text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
              >
                작성하기
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-40">
        {/* 히어로 섹션 */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            <span className="text-primary-600">AI</span> <span className="text-primary-600">리포트</span> 작성 도우미
          </h2>
          <p className="text-xl text-gray-600 mb-8">
            질문하시면 <span className="text-primary-600">AI</span>가 전문적인 <span className="text-primary-600">리포트</span> 작성을 도와드립니다
          </p>
        </div>

        {/* 검색 폼 */}
        <div className="max-w-3xl mx-auto mb-40">
          <form onSubmit={handleSearch} className="relative">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="어떤 리포트를 찾고 싶으신가요? (예: 아두이노 활용 보고서)"
                className="w-full px-6 py-4 text-lg border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent shadow-sm"
              />
              <button
                type="submit"
                disabled={!searchQuery.trim()}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-primary-600 text-white p-3 rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
            </div>
          </form>
        </div>

        {/* 기능 소개 */}
        <div className="mt-24">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">
                빠른 검색
              </h4>
              <p className="text-gray-600 text-sm">
                질문만 입력하면 다양한 관련 리포트를 찾아줍니다
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">
                정확한 분석
              </h4>
              <p className="text-gray-600 text-sm">
                최신 데이터와 AI 분석으로 신뢰할 수 있는 결과를 제공합니다
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
              </div>
              <h4 className="text-lg font-semibold text-gray-900 mb-2">
                다양한 형식
              </h4>
              <p className="text-gray-600 text-sm">
                비즈니스 리포트, 분석 보고서, 요약 문서 등 원하는 형식으로 작성
              </p>
            </div>
          </div>
        </div>

        {/* 사용 예시 */}
        <div className="mt-40 bg-white rounded-2xl p-8 shadow-sm">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">
            사용 예시
          </h3>
          <div className="space-y-6">
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-medium text-gray-600">Q</span>
              </div>
              <div className="flex-1">
                <p className="text-gray-900 font-medium">"아두이노 활용 보고서 찾아줘"</p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-sm font-medium text-primary-600">A</span>
              </div>
              <div className="flex-1">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-900 mb-2">아두이노 활용 보고서</h4>
                  <div className="space-y-2 text-sm text-gray-600">
                    <p>• 매출 현황 및 추이 분석</p>
                    <p>• 주요 성과 지표 (KPI) 분석</p>
                    <p>• 시장 동향 및 경쟁사 비교</p>
                    <p>• 향후 전략 및 개선 방안</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 푸터 */}
      <footer className="mt-20 bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-600">
            <p>&copy; 2025 ReportCoach. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default MainPage 