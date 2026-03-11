export const AUTH_TOKEN_STORAGE_KEY = "auth:token";

function getSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function readAuthToken(): string | null {
  const storage = getSessionStorage();
  const token = storage?.getItem(AUTH_TOKEN_STORAGE_KEY)?.trim();
  return token ? token : null;
}

export function writeAuthToken(token: string): void {
  const storage = getSessionStorage();
  if (!storage) {
    throw new Error("当前浏览器无法保存登录态");
  }
  storage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAuthToken(): void {
  getSessionStorage()?.removeItem(AUTH_TOKEN_STORAGE_KEY);
}
