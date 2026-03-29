import { useEffect } from 'react'
import Topbar from './Topbar'
import Sidebar from './Sidebar'
import useUiStore from '../../store/uiStore'

export default function AppShell({ children }) {
  const theme = useUiStore((s) => s.theme)
  const setTheme = useUiStore((s) => s.setTheme)

  useEffect(() => {
    const savedTheme = window.localStorage.getItem('copilot-theme')
    if (savedTheme) {
      setTheme(savedTheme)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    window.localStorage.setItem('copilot-theme', theme)
  }, [theme])

  return (
    <div className="min-h-screen pb-8">
      <Topbar />
      <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-5">
        <Sidebar />
        <main className="space-y-6">{children}</main>
      </div>
    </div>
  )
}
