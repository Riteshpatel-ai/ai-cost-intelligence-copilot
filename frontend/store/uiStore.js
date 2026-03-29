import { create } from 'zustand'

const useUiStore = create((set) => ({
  selectedDomain: 'all',
  theme: 'operations-light',
  setSelectedDomain: (selectedDomain) => set({ selectedDomain }),
  setTheme: (theme) => set({ theme }),
}))

export default useUiStore
