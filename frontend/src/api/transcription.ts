import client from './client'

export enum TranscriptionStatus {
  pending = 'pending',
  processing = 'processing',
  completed = 'completed',
  failed = 'failed',
}

export interface Transcription {
  id: string
  user_id: string
  filename: string
  file_size: number
  duration: number | null
  language: string | null
  status: TranscriptionStatus
  model_used: string
  created_at: string
}

export interface Segment {
  start_time: number
  end_time: number
  speaker_id: number | string
  text: string
}

export interface TranscriptionResult {
  segments: Segment[]
  language: string
  prompt_tokens: number
  generation_tokens: number
  total_tokens: number
  prompt_tps: number
  generation_tps: number
  total_time: number
}

export interface TranscriptionDetail extends Transcription {
  result_json: TranscriptionResult | null
  result_text: string | null
  error_message: string | null
  completed_at: string | null
}

export interface TranscriptionListResponse {
  items: Transcription[]
  total: number
  page: number
  page_size: number
  pages: number
}

export async function createTranscription(
  file: File,
  options?: {
    language?: string
    onProgress?: (percent: number) => void
  }
): Promise<Transcription> {
  const formData = new FormData()
  formData.append('file', file)
  if (options?.language) {
    formData.append('language', options.language)
  }

  const { data } = await client.post('/v1/transcriptions', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (options?.onProgress && progressEvent.total) {
        const percent = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
        options.onProgress(percent)
      }
    },
  })
  return data
}

export async function listTranscriptions(
  params?: {
    page?: number
    page_size?: number
    status?: TranscriptionStatus
  }
): Promise<TranscriptionListResponse> {
  const { data } = await client.get('/v1/transcriptions', { params })
  return data
}

export async function getTranscription(
  id: string
): Promise<TranscriptionDetail> {
  const { data } = await client.get(`/v1/transcriptions/${id}`)
  return data
}

export async function downloadTranscription(
  id: string,
  format: 'json' | 'txt' | 'srt' | 'vtt' | 'zip'
): Promise<void> {
  const response = await client.get(`/v1/transcriptions/${id}/download`, {
    params: { format },
    responseType: 'blob',
  })

  const contentDisposition = response.headers['content-disposition'] as
    | string
    | undefined
  let filename = `${id}.${format}`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match) filename = match[1]
  }

  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function deleteTranscription(id: string): Promise<void> {
  await client.delete(`/v1/transcriptions/${id}`)
}