import CategoryNav from "@/components/CategoryNav";
import SearchBar from "@/components/SearchBar";
import Link from "next/link";

export default function Home() {
  return (
    <div>
      {/* Hero 搜索区 */}
      <section className="text-center py-16">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          文山州知识库
        </h1>
        <p className="text-lg text-gray-500 mb-10">
          云南省文山壮族苗族自治州综合性知识服务平台
        </p>
        <SearchBar />
      </section>

      {/* 分类导航 */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">分类浏览</h2>
        <CategoryNav />
      </section>

      {/* 快速入口 */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <Link href="/notes?category=05-经济发展" className="block p-6 rounded-xl bg-white border hover:shadow-lg transition-shadow">
          <div className="text-3xl mb-3">📈</div>
          <h3 className="text-lg font-semibold mb-1">经济发展</h3>
          <p className="text-sm text-gray-500">绿色铝、三七产业、外贸数据</p>
        </Link>
        <Link href="/notes?category=06-文化旅游" className="block p-6 rounded-xl bg-white border hover:shadow-lg transition-shadow">
          <div className="text-3xl mb-3">🏞️</div>
          <h3 className="text-lg font-semibold mb-1">文化旅游</h3>
          <p className="text-sm text-gray-500">普者黑、坝美、老山圣地</p>
        </Link>
        <Link href="/notes?category=04-人口与民族" className="block p-6 rounded-xl bg-white border hover:shadow-lg transition-shadow">
          <div className="text-3xl mb-3">🎭</div>
          <h3 className="text-lg font-semibold mb-1">民族文化</h3>
          <p className="text-sm text-gray-500">壮族、坡芽歌书、非遗传承</p>
        </Link>
      </section>
    </div>
  );
}
