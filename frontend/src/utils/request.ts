/**
 * utils/request.ts - 统一 axios 请求封装
 * 严格 TS 类型，统一错误处理（ElementPlus 消息提示）
 */
import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL || ''
const REQUEST_TIMEOUT = 30_000

const instance: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json;charset=UTF-8',
  },
})

// 请求拦截：无 token（纯本地工具，无鉴权）
instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => config,
  (error: AxiosError) => Promise.reject(error),
)

// 响应拦截：后端 FastAPI 非 2xx 会直接进入 error
instance.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error: AxiosError<{ detail?: string }>) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    const msg = detail || error.message || '未知网络错误'

    if (status === 400) {
      ElMessage.error(`参数错误：${msg}`)
    } else if (status === 404) {
      ElMessage.error(`资源不存在：${msg}`)
    } else if (status && status >= 500) {
      ElMessage.error(`后端服务异常 (${status})：${msg}`)
    } else if (!status) {
      ElMessage.error(`网络连接失败：${msg}`)
    } else {
      ElMessage.error(`请求失败 (${status})：${msg}`)
    }
    return Promise.reject(error)
  },
)

// 严格类型的请求方法（全量覆盖配置中心 CRUD）
export function httpGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.get<unknown, T>(url, config)
}

export function httpPost<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return instance.post<unknown, T>(url, data, config)
}

export function httpPut<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  return instance.put<unknown, T>(url, data, config)
}

export function httpDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.delete<unknown, T>(url, config)
}

/** 文件上传（不写死 Content-Type，让 Axios 自动识别 FormData 的 boundary */
export function httpUpload<T>(
  url: string,
  formData: FormData,
): Promise<T> {
  return instance.request<unknown, T>({
    url,
    method: 'POST',
    data: formData,
    timeout: 120_000,
    headers: {
      // 不要手动设置 Content-Type: multipart/form-data，浏览器自动处理 boundary
    },
  })
}

export default instance
