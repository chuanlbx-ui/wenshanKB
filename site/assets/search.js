// WenShanKB Frontend Search
function doSearch(query) {
  const results = document.getElementById('searchResults');
  if (!query || query.trim().length < 1) {
    results.style.display = 'none';
    results.className = 'search-results';
    return;
  }
  
  const q = query.toLowerCase().trim();
  if (typeof SEARCH_INDEX === 'undefined') {
    results.innerHTML = '<div class="search-result-item"><p>搜索索引加载中...</p></div>';
    results.style.display = 'block';
    results.className = 'search-results show';
    return;
  }
  
  const matched = SEARCH_INDEX.filter(item => {
    const title = (item.title || '').toLowerCase();
    const tags = (item.tags || []).join(' ').toLowerCase();
    const category = (item.category || '').toLowerCase();
    return title.includes(q) || tags.includes(q) || category.includes(q);
  });
  
  if (matched.length === 0) {
    results.innerHTML = '<div class="search-result-item"><p>未找到匹配的笔记</p></div>';
  } else {
    const html = matched.slice(0, 20).map(item => {
      const tagsStr = (item.tags || []).map(t => `<span class="tag">${t}</span>`).join(' ');
      const conf = item.confidence ? `<span class="confidence confidence-${item.confidence}">${item.confidence}</span>` : '';
      return `<div class="search-result-item">
        <a href="${item.url}">${highlight(item.title, q)}</a>
        <div class="meta">${item.category} &middot; ${tagsStr} ${conf}</div>
      </div>`;
    }).join('');
    results.innerHTML = html + (matched.length > 20 ? `<p style="color:var(--text-muted);text-align:center">显示前 20 条，共 ${matched.length} 条结果</p>` : '');
  }
  
  results.style.display = 'block';
  results.className = 'search-results show';
}

function highlight(text, query) {
  if (!query) return text;
  const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(re, '<span class="search-highlight">$1</span>');
}

// Support nav search
document.addEventListener('DOMContentLoaded', function() {
  const navSearch = document.getElementById('navSearch');
  const heroSearch = document.getElementById('heroSearch');
  if (navSearch) {
    navSearch.addEventListener('keyup', function(e) {
      if (e.key === 'Enter') doSearch(this.value);
    });
  }
  if (heroSearch) {
    heroSearch.addEventListener('keyup', function(e) {
      if (e.key === 'Enter') doSearch(this.value);
    });
  }
});
