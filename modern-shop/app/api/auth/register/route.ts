import { NextResponse } from 'next/server';
import { createUser } from '@/lib/users';

export async function POST(request: Request) {
  const { email, password, name } = await request.json();

  if (!email || !password || !name) {
    return NextResponse.json({ message: 'Name, email, and password are required' }, { status: 400 });
  }

  try {
    const user = createUser({ email, password, name });
    return NextResponse.json({
      user: {
        id: user.id,
        email: user.email,
        name: user.name
      }
    });
  } catch (error) {
    return NextResponse.json({ message: error instanceof Error ? error.message : 'Unable to register' }, { status: 400 });
  }
}
