from django.urls import path
from apps.landing import landing_views, news_views

app_name = 'landing'

# URLs de páginas estáticas
url_home = [
    path('', landing_views.HomeView.as_view(), name='home'),
    path('about/', landing_views.AboutView.as_view(), name='about'),
    path('members/', landing_views.MembersView.as_view(), name='members'),
    path('magazine/', landing_views.MagazineView.as_view(), name='magazine'),
    path('contact/', landing_views.ContactView.as_view(), name='contact'),
    path('join/', landing_views.JoinView.as_view(), name='join'),
    path('refresh-captcha/', landing_views.refresh_captcha, name='refresh_captcha'),
]

# URLs de noticias
url_news = [
    path('news/', news_views.PostListView.as_view(), name='news_list'),
    path('news/<int:year>/<int:month>/<int:day>/<slug:post>/', news_views.PostDetailView.as_view(), name='new_detail'),
    # Vista filtrada por tags
    path('news/tag/<slug:tag_slug>/', news_views.PostListView.as_view(), name='news_list_by_tag'),
    # Vista filtrada por categorías
    path('news/category/<slug:category_slug>/', news_views.PostListView.as_view(), name='news_list_by_category'),
    path('news/comment/ajax/', news_views.CommentAjaxView.as_view(), name='comment_ajax'),
]

urlpatterns = url_home + url_news