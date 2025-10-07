/**
 * Capabilities Store
 * 
 * 使用 Zustand 管理模型能力数据，支持持久化
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { capabilitiesApi } from '@/services/api'

interface Capability {
    capability_id: number
    capability_name: string
    description?: string
}

interface CapabilitiesState {
    capabilities: Capability[]
    loading: boolean
    error: string | null
    lastFetchTime: number | null
    
    // Actions
    fetchCapabilities: (force?: boolean) => Promise<void>
    clearCapabilities: () => void
}

// 缓存有效期（5分钟）
const CACHE_DURATION = 5 * 60 * 1000

export const useCapabilitiesStore = create<CapabilitiesState>()(
    persist(
        (set, get) => ({
            capabilities: [],
            loading: false,
            error: null,
            lastFetchTime: null,

            fetchCapabilities: async (force = false) => {
                const state = get()
                const now = Date.now()
                
                // 如果不是强制刷新，且缓存有效，则不重新获取
                if (
                    !force &&
                    state.capabilities.length > 0 &&
                    state.lastFetchTime &&
                    now - state.lastFetchTime < CACHE_DURATION
                ) {
                    return
                }

                set({ loading: true, error: null })

                try {
                    const response: any = await capabilitiesApi.getCapabilities()
                    set({
                        capabilities: response.data?.capabilities || [],
                        loading: false,
                        error: null,
                        lastFetchTime: now,
                    })
                } catch (error) {
                    console.error('Failed to fetch capabilities:', error)
                    set({
                        loading: false,
                        error: '获取能力列表失败',
                    })
                }
            },

            clearCapabilities: () => {
                set({
                    capabilities: [],
                    loading: false,
                    error: null,
                    lastFetchTime: null,
                })
            },
        }),
        {
            name: 'capabilities-storage', // localStorage key
            storage: createJSONStorage(() => localStorage),
            // 只持久化 capabilities 和 lastFetchTime
            partialize: (state) => ({
                capabilities: state.capabilities,
                lastFetchTime: state.lastFetchTime,
            }),
        }
    )
)
