import { describe, expect, it, vi } from "vitest";

import {
  completeRegisterVerification,
  requestRegisterCaptcha,
  startRegisterVerification,
} from "./authRegistration";
import { LearningCoachApi } from "./apiClient";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
  });
}

describe("registration verification API flow", () => {
  it("requests captcha, starts email verification, then completes registration", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          captcha_id: "captcha-1",
          image_data_url: "data:image/png;base64,abc",
          expires_in_seconds: 300,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          verification_id: "verification-1",
          email: "learner@example.com",
          expires_in_seconds: 600,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          token: "session-token",
          user: {
            user_id: "u1",
            name: "Learner",
            email: "learner@example.com",
            role: "learner",
          },
        }),
      );
    const api = new LearningCoachApi({ baseUrl: "/", fetcher });

    await requestRegisterCaptcha(api);
    await startRegisterVerification(api, {
      name: "Learner",
      email: "learner@example.com",
      password: "password123",
      captcha_id: "captcha-1",
      captcha_code: "ABCDE",
    });
    await completeRegisterVerification(api, "verification-1", "123456");

    expect(fetcher.mock.calls.map(([url]) => url)).toEqual([
      "/auth/register/captcha",
      "/auth/register/start",
      "/auth/register/complete",
    ]);
    expect(fetcher.mock.calls[1][1].body).toBe(
      JSON.stringify({
        name: "Learner",
        email: "learner@example.com",
        password: "password123",
        captcha_id: "captcha-1",
        captcha_code: "ABCDE",
      }),
    );
    expect(fetcher.mock.calls[2][1].body).toBe(
      JSON.stringify({ verification_id: "verification-1", email_code: "123456" }),
    );
  });
});
