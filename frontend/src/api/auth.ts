import apiClient from './client'
import type { AuthRequest, LoginResponse, UserInfo, ChangePasswordRequest } from '../types'

export async function login(data: AuthRequest): Promise<LoginResponse> {
  const res = await apiClient.post('/auth/login', data)
  return res.data.data
}

export async function register(data: AuthRequest): Promise<UserInfo> {
  const res = await apiClient.post('/auth/register', data)
  return res.data.data
}

export async function getMe(): Promise<UserInfo> {
  const res = await apiClient.get('/auth/me')
  return res.data.data
}

export async function changePassword(data: ChangePasswordRequest): Promise<void> {
  await apiClient.put('/auth/change-password', data)
}
