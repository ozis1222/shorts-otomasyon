export const dynamic = 'force-dynamic';

export default function AdminLogin({ searchParams }: { searchParams: { error?: string } }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-paper text-ink">
      <form action="/api/admin/login" method="post" className="w-full max-w-sm rounded-2xl border border-hair bg-white p-8">
        <p className="text-xs font-bold uppercase tracking-[0.3em] text-ember">The Us Archive</p>
        <h1 className="mt-2 font-editorial text-2xl">Seller dashboard</h1>
        <label className="mt-6 mb-1 block text-sm font-medium">Password</label>
        <input
          type="password"
          name="password"
          required
          autoFocus
          className="w-full rounded-xl border border-hair px-4 py-3 outline-none focus:border-ember"
        />
        {searchParams.error && <p className="mt-3 text-sm text-red-600">Incorrect password.</p>}
        <button className="mt-6 w-full rounded-full bg-ink px-6 py-3 font-semibold text-white hover:opacity-90">Sign in</button>
      </form>
    </main>
  );
}
