from django.urls import path, reverse_lazy
from apps.panel import dashboard_views, post_views
# TODO: Cuando las vistas crezcan, importar desde módulos específicos:
# from apps.panel import post_views, category_views, comment_views

app_name = 'dashboard'

urlpatterns = [
    # =====================================================================
    # PANEL PRINCIPAL Y MÓDULOS BASE
    # =====================================================================
    path('', dashboard_views.DashBoardView.as_view(), name='dashboard'),
    
    # --- Módulo: Socios ---
    path('members/', dashboard_views.MembersView.as_view(), name='members'),
    
    # --- Módulo: Finanzas ---
    path('billing/', dashboard_views.BillingView.as_view(), name='billing'),
    path('expenses/', dashboard_views.ExpensesView.as_view(), name='expenses'),
    path('balance/', dashboard_views.BalanceView.as_view(), name='balance'),
    
    # --- Módulo: Estrategia ---
    path('plan/', dashboard_views.PlanView.as_view(), name='plan'),

    # =====================================================================
    # GESTIÓN DE CONTENIDO - POSTS/NOTICIAS
    # =====================================================================
    # TODO: Cambiar dashboard_views por post_views cuando se modularice
    
    # --- CRUD Principal de Posts ---
    path('posts/', post_views.PostListView.as_view(), name='post-list'),
    path('posts/create/', post_views.PostCreateView.as_view(), name='post-create'),
    path('posts/<str:pk>/update/', post_views.PostUpdateView.as_view(), name='post-update'),
    
    # --- Acciones Masivas de Posts ---
    path('posts/bulk/delete/', post_views.PostBulkDeleteView.as_view(), name='post-bulk-delete'),
    path('posts/bulk/status/', post_views.PostBulkStatusView.as_view(), name='post-bulk-status'),
    path('posts/export/', post_views.PostExportView.as_view(), name='post-export'),
    path('posts/cache/clear/', post_views.PostClearCacheView.as_view(), name='post-clear-cache'),
    
    # --- Inteligencia Artificial para Posts ---
    path('posts/ai/generate/', post_views.GetNewPostAI.as_view(), name='post-generate-ai-content'),
    path('posts/ai/translations/', post_views.GeneratePostTranslationsAI.as_view(), name='post-generate-translations'),
    path('posts/ai/regenerate-meta/<str:pk>/', post_views.PostRegenerateMetaView.as_view(), name='post-regenerate-meta'),
    path('posts/ai/check-task/', post_views.CheckAITaskStatus.as_view(), name='post-check-ai-task'),
    
    # --- APIs y Búsquedas ---
    path('posts/api/stats/', post_views.DashboardStatsAPIView.as_view(), name='stats-api'),
    path('posts/search/', post_views.PostSearchView.as_view(), name='posts-search'),

    # =====================================================================
    # GESTIÓN DE TAXONOMÍAS DE POSTS
    # =====================================================================
    # TODO: Cambiar dashboard_views por category_views y tag_views cuando se modularice
    
    # --- Categorías ---
    path('posts/categories/', post_views.CategoryListView.as_view(), name='category-list'),
    path('posts/categories/create/', post_views.CategoryCreateView.as_view(), name='category-create'),
    path('posts/categories/<int:pk>/update/', post_views.CategoryUpdateView.as_view(), name='category-update'),
    path('posts/categories/<int:pk>/delete/', post_views.CategoryDeleteView.as_view(), name='category-delete'),
    
    # --- Etiquetas (Tags) ---
    path('posts/tags/', post_views.TagListView.as_view(), name='tag-list'),
    path('posts/tags/create/', post_views.TagCreateView.as_view(), name='tag-create'),
    path('posts/tags/<int:pk>/update/', post_views.TagUpdateView.as_view(), name='tag-update'),
    path('posts/tags/<int:pk>/delete/', post_views.TagDeleteView.as_view(), name='tag-delete'),

    # =====================================================================
    # GESTIÓN DE INTERACCIONES DE POSTS
    # =====================================================================
    # TODO: Cambiar dashboard_views por comment_views cuando se modularice
    
    # --- Comentarios ---
    path('posts/comments/', post_views.CommentListView.as_view(), name='comment-list'),
    path('posts/<str:pk>/comments/', post_views.CommentManageView.as_view(), name='comment-manage'),  # Comentarios de un post específico
    path('posts/comments/<int:pk>/delete/', post_views.CommentDeleteView.as_view(), name='comment-delete'),
    path('posts/comments/<int:pk>/update/', post_views.CommentUpdateView.as_view(), name='comment-update'),

    # =====================================================================
    # GESTIÓN DE CONTACTOS
    # =====================================================================
    path('contacts/', dashboard_views.ContactMessageListView.as_view(), name='contact-list'),
    path('contacts/<int:pk>/delete/', dashboard_views.ContactMessageDeleteView.as_view(), name='contact-delete'),
    path('contacts/export/', dashboard_views.ContactMessageExportView.as_view(), name='contact-export'),
    path('contacts/<int:pk>/mark-read/', dashboard_views.ContactMarkReadView.as_view(), name='contact-mark-read'), #visto o no  
    path('contacts/<int:pk>/answer/', dashboard_views.ContactMessageAnswerView.as_view(), name='contact-answer'), # RESPONDIDO O NO
    path('contacts/<int:pk>/replies/', dashboard_views.ContactRepliesView.as_view(), name='contact-replies'), # Obtener respuestas
]
