import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Puzzle, User, LogOut } from 'lucide-react'

export const Navbar: React.FC = () => {
  const navigate = useNavigate()
  const isAuthenticated = false // TODO: 실제 인증 상태 관리

  const handleLogout = () => {
    // TODO: 로그아웃 로직 구현
    navigate('/')
  }

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* 로고 */}
          <Link to="/" className="flex items-center space-x-2">
            <Puzzle className="h-8 w-8 text-primary-600" />
            <span className="text-xl font-bold text-gradient">
              PuzzleCraft AI
            </span>
          </Link>

          {/* 네비게이션 메뉴 */}
          <div className="hidden md:flex items-center space-x-8">
            <Link
              to="/"
              className="text-gray-600 hover:text-primary-600 transition-colors"
            >
              홈
            </Link>
            {isAuthenticated && (
              <>
                <Link
                  to="/dashboard"
                  className="text-gray-600 hover:text-primary-600 transition-colors"
                >
                  대시보드
                </Link>
                <Link
                  to="/puzzle/create"
                  className="text-gray-600 hover:text-primary-600 transition-colors"
                >
                  퍼즐 생성
                </Link>
              </>
            )}
          </div>

          {/* 사용자 메뉴 */}
          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <Link
                  to="/profile"
                  className="flex items-center space-x-2 text-gray-600 hover:text-primary-600 transition-colors"
                >
                  <User className="h-5 w-5" />
                  <span className="hidden md:inline">프로필</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 text-gray-600 hover:text-red-600 transition-colors"
                >
                  <LogOut className="h-5 w-5" />
                  <span className="hidden md:inline">로그아웃</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <Link
                  to="/login"
                  className="text-gray-600 hover:text-primary-600 transition-colors"
                >
                  로그인
                </Link>
                <Link
                  to="/register"
                  className="btn-primary"
                >
                  회원가입
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}