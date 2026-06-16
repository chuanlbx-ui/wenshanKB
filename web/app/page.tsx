import CategoryNav from "@/components/CategoryNav";
import SearchBar from "@/components/SearchBar";
import Link from "next/link";

// 首页是服务端组件，热门笔记通过客户端 API 调用获取
// 这里做一个静态的热门入口 + 客户端加载的热门区块

export default function Home() {
  return (
    <div>
      {/* Hero 搜索区 */}
      <section className="text-center py-16">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-3">
          文山州知识库
        </h1>
        <p className="text-lg text-gray-500 dark:text-gray-400 dark:text-gray-500 mb-10">
          云南省文山壮族苗族自治州综合性知识服务平台
        </p>
        <SearchBar />
      </section>

      {/* 分类导航 */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">分类浏览</h2>
        <CategoryNav />
      </section>

      {/* 快速入口 */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
        <Link href="/notes?category=05-经济发展" className="block p-5 rounded-xl bg-gradient-to-br from-blue-50 to-white border border-blue-100 hover:shadow-lg transition-all group">
          <div className="text-3xl mb-2">📈</div>
          <h3 className="text-lg font-semibold mb-1 group-hover:text-blue-600 transition-colors">经济发展</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 dark:text-gray-500">绿色铝、三七产业、外贸数据</p>
        </Link>
        <Link href="/notes?category=06-文化旅游" className="block p-5 rounded-xl bg-gradient-to-br from-emerald-50 to-white border border-emerald-100 hover:shadow-lg transition-all group">
          <div className="text-3xl mb-2">🏞️</div>
          <h3 className="text-lg font-semibold mb-1 group-hover:text-emerald-600 transition-colors">文化旅游</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 dark:text-gray-500">普者黑、坝美、老山圣地</p>
        </Link>
        <Link href="/notes?category=04-人口与民族" className="block p-5 rounded-xl bg-gradient-to-br from-purple-50 to-white border border-purple-100 hover:shadow-lg transition-all group">
          <div className="text-3xl mb-2">🎭</div>
          <h3 className="text-lg font-semibold mb-1 group-hover:text-purple-600 transition-colors">民族文化</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 dark:text-gray-500">壮族、坡芽歌书、非遗传承</p>
        </Link>
      </section>

      {/* 全部笔记入口 */}
      <section className="text-center">
        <Link
          href="/notes"
          className="inline-block px-8 py-3 bg-primary text-white rounded-full hover:bg-blue-700 transition-colors shadow-sm"
        >
          浏览全部 200+ 篇笔记 →
        </Link>
      </section>
    </div>
  );
}
