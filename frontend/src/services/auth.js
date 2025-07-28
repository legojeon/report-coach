import api from "./api";

export const signup = async (data) => {
  const res = await api.post("/auth/register", data);
  return res.data;
};

export const login = async (data) => {
  const res = await api.post("/auth/login", data);
  return res.data;
};

export const getMe = async (token) => {
  const res = await api.get("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.data;
};

export const deleteAccount = async (token, userId) => {
  const res = await api.delete(`/users/${userId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.data;
}; 