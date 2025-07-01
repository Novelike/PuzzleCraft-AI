import React from 'react'
import { Link } from 'react-router-dom'
import { Upload, Sparkles, Users, Trophy } from 'lucide-react'

export const Home: React.FC = () => {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            AI로 만드는 나만의{' '}
            <span className="text-gradient">퍼즐 게임</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">
            사진을 업로드하면 AI가 자동으로 퍼즐을 생성합니다.
            <br />
            친구들과 함께 즐기거나 혼자서 도전해보세요!
          </p>
          <div className="flex justify-center space-x-4">
            <Link to="/register" className="btn-primary text-lg px-8 py-3">
              지금 시작하기
            </Link>
            <Link 
              to="/puzzle/create" 
              className="btn-secondary text-lg px-8 py-3"
            >
              퍼즐 만들기
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            PuzzleCraft AI의 특별한 기능들
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="card text-center">
              <Upload className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">간편한 업로드</h3>
              <p className="text-gray-600">
                사진을 드래그하거나 클릭만으로 쉽게 업로드하세요
              </p>
            </div>
            <div className="card text-center">
              <Sparkles className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">AI 자동 생성</h3>
              <p className="text-gray-600">
                AI가 이미지를 분석하여 최적의 퍼즐 조각을 생성합니다
              </p>
            </div>
            <div className="card text-center">
              <Users className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">멀티플레이</h3>
              <p className="text-gray-600">
                친구들과 실시간으로 함께 퍼즐을 완성해보세요
              </p>
            </div>
            <div className="card text-center">
              <Trophy className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">랭킹 시스템</h3>
              <p className="text-gray-600">
                다른 플레이어들과 점수를 경쟁하고 순위를 확인하세요
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-primary-600 to-purple-600">
        <div className="max-w-4xl mx-auto text-center text-white">
          <h2 className="text-3xl font-bold mb-6">
            지금 바로 시작해보세요!
          </h2>
          <p className="text-xl mb-8 opacity-90">
            무료로 회원가입하고 첫 번째 퍼즐을 만들어보세요
          </p>
          <Link 
            to="/register" 
            className="bg-white text-primary-600 font-semibold px-8 py-3 rounded-lg hover:bg-gray-100 transition-colors"
          >
            무료 회원가입
          </Link>
        </div>
      </section>
    </div>
  )
}