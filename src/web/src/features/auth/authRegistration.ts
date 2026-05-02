import type { ApiResponse, LearningCoachApi } from "../../api/apiClient";

export interface AuthUser {
  user_id: string;
  name: string;
  email: string;
  role: "learner" | "admin";
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

export interface RegisterCaptchaResponse {
  captcha_id: string;
  image_data_url: string;
  expires_in_seconds: number;
}

export interface RegisterStartResponse {
  verification_id: string;
  email: string;
  expires_in_seconds: number;
}

export interface RegisterStartInput {
  name: string;
  email: string;
  password: string;
  captcha_id: string;
  captcha_code: string;
}

export async function requestRegisterCaptcha(
  api: LearningCoachApi,
): Promise<ApiResponse<RegisterCaptchaResponse>> {
  return api.request<RegisterCaptchaResponse>("/auth/register/captcha");
}

export async function startRegisterVerification(
  api: LearningCoachApi,
  input: RegisterStartInput,
): Promise<ApiResponse<RegisterStartResponse>> {
  return api.request<RegisterStartResponse>("/auth/register/start", {
    method: "POST",
    body: input,
  });
}

export async function completeRegisterVerification(
  api: LearningCoachApi,
  verificationId: string,
  emailCode: string,
): Promise<ApiResponse<AuthResponse>> {
  return api.request<AuthResponse>("/auth/register/complete", {
    method: "POST",
    body: { verification_id: verificationId, email_code: emailCode },
  });
}
