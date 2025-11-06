export type User = {
  id: string;
  email: string;
  name: string;
  password: string;
};

const defaultAdmin = {
  id: 'admin',
  email: process.env.ADMIN_EMAIL ?? 'admin@example.com',
  name: 'Store Admin',
  password: process.env.ADMIN_PASSWORD ?? 'change_me'
};

export const users: User[] = [defaultAdmin];

export function createUser(user: Omit<User, 'id'>) {
  const existing = users.find((existingUser) => existingUser.email === user.email);
  if (existing) {
    throw new Error('Email already registered');
  }
  const newUser: User = { ...user, id: `user_${users.length + 1}` };
  users.push(newUser);
  return newUser;
}

export function validateUser(email: string, password: string) {
  return users.find((user) => user.email === email && user.password === password);
}
