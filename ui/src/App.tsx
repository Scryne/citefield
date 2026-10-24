import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Tooltip } from '@base-ui/react/tooltip'
import { FileQuestion } from 'lucide-react'
import { useEffect } from 'react'
import { AppShell, Page } from './components/AppShell'
import { Card, EmptyState } from './components/ui'
import { buttonClass } from './components/styles'
import { linkProps, useLocation } from './lib'
import { Documents } from './pages/Documents'
import { Overview } from './pages/Overview'
import { Review } from './pages/Review'
import { SchemaDetail } from './pages/SchemaDetail'
import { Schemas } from './pages/Schemas'
import { Settings } from './pages/Settings'

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } })

function route(path: string, query: URLSearchParams): { title: string; node: React.ReactNode } {
  const doc = path.match(/^\/d\/([\w-]+)$/)
  if (doc) return { title: 'Review', node: <Review key={doc[1]} id={doc[1]} /> }
  const schema = path.match(/^\/schemas\/([A-Za-z0-9_-]+)$/)
  if (path === '/') return { title: 'Overview', node: <Overview /> }
  if (path === '/documents') return { title: 'Documents', node: <Documents /> }
  if (path === '/schemas') return { title: 'Schemas', node: <Schemas /> }
  if (path === '/schemas/new')
    return { title: 'New schema', node: <SchemaDetail key="new" name={null} edit from={query.get('from')} /> }
  if (schema)
    return {
      title: schema[1],
      node: <SchemaDetail key={schema[1]} name={schema[1]} edit={query.has('edit')} from={null} />,
    }
  if (path === '/settings') return { title: 'Settings', node: <Settings /> }
  return {
    title: 'Not found',
    node: (
      <Page>
        <Card>
          <EmptyState
            icon={FileQuestion}
            title="This page does not exist"
            action={
              <a {...linkProps('/')} className={buttonClass('primary')}>
                Go to the overview
              </a>
            }
          >
            The address may be mistyped, or the document was deleted.
          </EmptyState>
        </Card>
      </Page>
    ),
  }
}

function Routes() {
  const { path, query } = useLocation()
  const { title, node } = route(path, query)
  useEffect(() => {
    document.title = `${title} · Citefield`
    window.scrollTo(0, 0)
  }, [title, path])
  return node
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Tooltip.Provider delay={300}>
        <AppShell>
          <Routes />
        </AppShell>
      </Tooltip.Provider>
    </QueryClientProvider>
  )
}
