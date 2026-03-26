export default function Home() {
  return (
    <main className="min-h-screen bg-bg-primary text-white">
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-primary mb-4">EcoSync</h1>
          <p className="text-xl text-gray-400 mb-8">AI-Driven Urban Sustainability Platform</p>
          <a
            href="/dashboard/city"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-bg-primary font-semibold rounded-lg hover:bg-primary-light transition-colors"
          >
            Launch Dashboard
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </a>
        </div>
      </div>
    </main>
  )
}
