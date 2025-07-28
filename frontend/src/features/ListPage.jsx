import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

// 인증된 이미지 컴포넌트 -> 인증 없는 이미지 컴포넌트로 변경
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

function ListPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [searchResults, setSearchResults] = useState([])
  const [showResults, setShowResults] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [showAnalysis, setShowAnalysis] = useState(false)
  const [showProUpgrade, setShowProUpgrade] = useState(false)
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const isInitialMount = useRef(true)
  
  // 페이지네이션 관련 상태 추가
  const [displayedResults, setDisplayedResults] = useState([])
  const [currentPage, setCurrentPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  
  // 검색 및 분석 설정 (상단에서 관리)
  const resultsPerPage = 10        // 페이지네이션 단위
  const searchResultCount = 50     // 검색 결과 개수
  const analysisResultCount = 5    // 분석 대상 개수
  
  // 정렬 옵션 상태 추가
  const [sortOption, setSortOption] = useState('relevance') // 'relevance' 또는 'latest'

  useEffect(() => {
    const token = localStorage.getItem('token')
    setIsLoggedIn(!!token)
    
    // 로그인하지 않은 경우 로그인 페이지로 리다이렉트
    if (!token) {
      navigate('/login')
      return
    }
    
    // URL 파라미터에서 검색어 가져오기 (초기 마운트 시에만)
    if (isInitialMount.current) {
      const query = searchParams.get('q')
      if (query && query !== searchQuery) {
        setSearchQuery(query)
        handleSearchFromURL(query)
      }
      isInitialMount.current = false
    }
  }, [searchParams, searchQuery, navigate])

  // 검색 결과가 변경될 때 페이지네이션 초기화
  useEffect(() => {
    if (searchResults.length > 0) {
      setCurrentPage(1)
      setDisplayedResults(searchResults.slice(0, resultsPerPage))
      setHasMore(searchResults.length > resultsPerPage)
    } else {
      setDisplayedResults([])
      setHasMore(false)
    }
  }, [searchResults])

  // 정렬 옵션이 변경될 때 결과 재정렬
  useEffect(() => {
    if (searchResults.length > 0) {
      let sortedResults = [...searchResults]
      
      if (sortOption === 'latest') {
        // 최신순 정렬 (년도 내림차순)
        sortedResults.sort((a, b) => {
          const yearA = parseInt(a.metadata.year) || 0
          const yearB = parseInt(b.metadata.year) || 0
          return yearB - yearA // 내림차순 (최신이 위로)
        })
      }
      // 관련도순은 기존 순서 유지 (searchResults가 이미 관련도순으로 정렬됨)
      
      setCurrentPage(1)
      setDisplayedResults(sortedResults.slice(0, resultsPerPage))
      setHasMore(sortedResults.length > resultsPerPage)
    }
  }, [sortOption, searchResults])

  const handleSearchFromURL = async (query) => {
    // URL 파라미터로 들어온 검색어를 searchQuery에 설정
    setSearchQuery(query)
    
    // 공통 검색 로직 사용
    await performSearch(query)
  }

  const performSearch = async (query) => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/login')
      return
    }

    setIsSearching(true)
    setShowResults(false)
    setShowAnalysis(false)
    setShowProUpgrade(false)
    setAnalysisResult(null)
    
    try {
      // 먼저 사용자 정보를 가져와서 is_membership 확인
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const userResponse = await fetch(`${apiUrl}/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      let userData = null
      if (userResponse.ok) {
        userData = await userResponse.json()
        console.log('사용자 is_membership:', userData.is_membership)
      }

      const response = await fetch(`${apiUrl}/search/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: query,
          k: searchResultCount  // 더 많은 결과를 가져와서 페이지네이션에 사용
        })
      })

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('token')
          navigate('/login')
          return
        }
        throw new Error('검색 요청에 실패했습니다.')
      }

      const data = await response.json()
      setSearchResults(data.results || [])
      setShowResults(true)
      
      // 쿼리 의도가 "분석"인 경우 분석 API 호출
      // if (data.intent === "분석") {
      //   await handleAnalysis(query, userData, data.results)
      // }
      await handleAnalysis(query, userData, data.results)
      
    } catch (error) {
      alert('검색 중 오류가 발생했습니다.')
    } finally {
      setIsSearching(false)
    }
  }

  const handleAnalysis = async (query, userData, searchResults) => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/login')
      return
    }

    // is_membership이 false인 경우 Pro 업그레이드 메시지 표시
    if (userData && !userData.is_membership) {
      setShowProUpgrade(true)
      return
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/search/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: query,
          k: analysisResultCount,
          search_results: searchResults
        })
      })

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('token')
          navigate('/login')
          return
        }
        throw new Error('분석 요청에 실패했습니다.')
      }

      const data = await response.json()
      setAnalysisResult(data.analysis)
      setShowAnalysis(true)
    } catch (error) {
      // 분석 실패해도 검색 결과는 계속 표시
    }
  }

  // 더보기 버튼 클릭 핸들러
  const handleLoadMore = () => {
    setIsLoadingMore(true)
    
    // 현재 정렬된 결과 가져오기
    let sortedResults = [...searchResults]
    if (sortOption === 'latest') {
      sortedResults.sort((a, b) => {
        const yearA = parseInt(a.metadata.year) || 0
        const yearB = parseInt(b.metadata.year) || 0
        return yearB - yearA
      })
    }
    
    // 다음 페이지 계산
    const nextPage = currentPage + 1
    const startIndex = (nextPage - 1) * resultsPerPage
    const endIndex = startIndex + resultsPerPage
    
    // 새로운 결과 추가
    const newResults = sortedResults.slice(startIndex, endIndex)
    setDisplayedResults(prev => [...prev, ...newResults])
    setCurrentPage(nextPage)
    
    // 더 로드할 결과가 있는지 확인
    setHasMore(endIndex < sortedResults.length)
    
    setIsLoadingMore(false)
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (searchQuery.trim() && !isSearching) {
      // URL 파라미터 업데이트
      setSearchParams({ q: searchQuery })
      
      // 공통 검색 로직 사용
      await performSearch(searchQuery)
    }
  }

  const handleMembershipClick = () => {
    navigate('/plan');
  };

  const handleLogoClick = () => {
    navigate('/');
  };

  const handleWriteClick = () => {
    navigate('/write');
  };

  const handleMyNotesClick = () => {
    navigate('/notes');
  };

  // 로그인하지 않은 경우 로딩 화면 표시
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">로그인 확인 중...</p>
        </div>
      </div>
    )
  }

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
                      <path fillRule="evenodd" d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8m8-7a7 7 0 00-5.468 11.37C3.242 11.226 4.805 10 8 10s4.757 1.225 5.468 2.37A7 7 0 008 1" />
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
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        {/* 검색 폼 */}
        <div className="mb-8">
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
                disabled={!searchQuery.trim() || isSearching}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-primary-600 text-white p-3 rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSearching ? (
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* 분석 결과 */}
        {showAnalysis && analysisResult && (
          <div className="mb-8">
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <h3 className="ml-3 text-lg font-semibold text-blue-900">
                  AI 분석 결과
                </h3>
              </div>
              <div className="prose prose-blue max-w-none">
                <ReactMarkdown>{analysisResult}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* Pro 업그레이드 메시지 */}
        {showProUpgrade && (
          <div className="mb-8">
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-semibold text-blue-900">
                      Pro 가입 시 이용 가능한 서비스입니다
                    </h3>
                    <p className="text-blue-700 mt-1">
                      AI 분석 기능을 이용하시려면 Pro 멤버십으로 업그레이드해주세요.
                    </p>
                  </div>
                </div>
                <button 
                  onClick={handleMembershipClick}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors ml-4"
                >
                  Pro 멤버십 가입하기
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 검색 결과 */}
        {showResults && (
          <div className="mb-8">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-2xl font-bold text-gray-900">
                검색 결과 ({searchResults.length}개)
              </h3>
              
              {/* 정렬 옵션 */}
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-3">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="sortOption"
                      value="relevance"
                      checked={sortOption === 'relevance'}
                      onChange={(e) => setSortOption(e.target.value)}
                      className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">관련도순</span>
                  </label>
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="sortOption"
                      value="latest"
                      checked={sortOption === 'latest'}
                      onChange={(e) => setSortOption(e.target.value)}
                      className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">최신순</span>
                  </label>
                </div>
              </div>
            </div>
            <div className="space-y-6">
              {displayedResults.map((result, index) => (
                <div 
                  key={index} 
                  className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => {
                    const data = encodeURIComponent(JSON.stringify(result));
                    window.open(`/chat?data=${data}`, '_blank');
                  }}
                >
                  <div className="flex gap-6">
                    {/* 텍스트 콘텐츠 섹션 */}
                    <div className="flex-1">
                      <div className="mb-4">
                        <h4 className="text-lg font-semibold text-gray-900 mb-2">
                          {result.title}
                        </h4>
                        <div className="flex flex-wrap gap-2 mb-3">
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                            {result.metadata.field}
                          </span>
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                            {result.metadata.year}
                          </span>
                          <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                            {result.metadata.award}
                          </span>
                          <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full">
                            {result.section}
                          </span>
                        </div>
                      </div>
                      
                      <div className="mb-4">
                        <p className="text-gray-600 text-sm leading-relaxed line-clamp-3">
                          {result.content}
                        </p>
                      </div>
                    </div>
                    
                    {/* 이미지 섹션 */}
                    {result.image_path && (
                      <div className="flex-shrink-0">
                        <AuthenticatedImage
                          reportNumber={result.number}
                          className="w-32 h-32 object-cover rounded-lg border border-gray-200"
                          alt={`보고서 ${result.number} 이미지`}
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            {/* 더보기 버튼 */}
            {hasMore && (
              <div className="text-center mt-8">
                <button
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  className="text-primary-600 hover:text-primary-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoadingMore ? (
                    <div className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      로딩 중...
                    </div>
                  ) : (
                    `더보기 (${displayedResults.length}/${searchResults.length})`
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {/* 검색 결과가 없을 때 */}
        {showResults && searchResults.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-3.042 0-5.824-1.135-7.938-3M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-3.042 0-5.824-1.135-7.938-3" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">검색 결과가 없습니다</h3>
            <p className="text-gray-500">다른 키워드로 검색해보세요.</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default ListPage 