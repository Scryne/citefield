import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DocumentList } from './pages/DocumentList'
import { Review } from './pages/Review'
import { navigate, usePath } from './lib'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

function Routes() {
  const path = usePath()
  const doc = path.match(/^\/d\/([\w-]+)$/)
  return doc ? <Review key={doc[1]} id={doc[1]} /> : <DocumentList />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex min-h-dvh flex-col">
        <nav className="glass sticky top-0 z-10 flex h-12 items-center gap-2 border-b px-4">
          <a
            href="/"
            onClick={(e) => {
              e.preventDefault()
              navigate('/')
            }}
            className="flex items-center gap-2 font-semibold"
          >
            <svg aria-hidden viewBox="0 0 20 20" className="size-5">
              <rect x="2" y="3" width="11" height="14" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
              <rect x="8" y="9" width="10" height="5" rx="1" fill="var(--color-primary-fill)" stroke="var(--color-primary)" strokeWidth="1.5" />
            </svg>
            Citefield
          </a>
          <span className="text-xs text-muted">self-hosted</span>
        </nav>
        <Routes />
      </div>
    </QueryClientProvider>
  )
}
