import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../services/auth'

function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login({ email, password })
      localStorage.setItem('token', res.access_token)
      navigate('/')
    } catch (err) {
      console.error('로그인 에러:', err)
      setError('이메일 또는 비밀번호가 올바르지 않습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-white">
      <form className="w-full max-w-xs flex flex-col items-center gap-4" onSubmit={handleSubmit}>
        <div className="mb-6 w-full text-center">
          <p className="text-lg text-gray-800 font-medium"><span className="text-primary-600">탐구코치</span>와 함께 보고서를 만들어보세요</p>
        </div>
        <input
          type="email"
          placeholder="이메일을 입력하세요"
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full bg-transparent border-b border-neutral-300 text-gray-900 placeholder-neutral-400 py-3 px-2 focus:outline-none focus:border-primary-500 transition"
        />
        <input
          type="password"
          placeholder="비밀번호를 입력하세요"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="w-full bg-transparent border-b border-neutral-300 text-gray-900 placeholder-neutral-400 py-3 px-2 focus:outline-none focus:border-primary-500 transition"
        />
        {error && <div className="text-red-500 text-sm w-full text-center">{error}</div>}
        <button
          type="submit"
          className="w-full mt-2 bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 rounded-lg transition-colors"
          disabled={loading}
        >
          {loading ? '로그인 중...' : '로그인'}
        </button>
      </form>
      <div className="flex flex-col items-center gap-2 mt-8">
        <button className="text-sm text-neutral-500 hover:text-primary-600 transition" onClick={() => navigate('/signup')}>회원가입</button>
        <button className="text-sm text-neutral-400 hover:text-neutral-600 transition mt-2" onClick={() => navigate('/')}>닫기</button>
      </div>
    </div>
  )
}

export default LoginPage 