from django.shortcuts import render

# Create your views here.
def dashboard(request):
    return render(request, "dashboards/padrao.html",context = 
        {
        'pipeline': {
            'nome': 'Captação de Imóveis',  # Ou o objeto Pipeline do seu modelo
        },
        'pipeline_metrics': {
            'created_count': 125,
            'completed_count': 80,
            'conversion_percent': "64% de conversão",
            'overdue_count': 7,
            'overdue_percent': "5.6% do total",
            'avg_completion_time': "4,5 dias",
            'target_time': "4 dias",
            'sla_percent_on_time': 67,
            'created_trend': [120, 130, 125, 140, 135],
            'completed_trend': [60, 70, 65, 80, 75],
            'overdue_trend': [5, 6, 7, 6, 8],
            'avg_time_trend': [4.8, 4.6, 4.7, 4.5, 4.3],
        },
        'flow_categories': ['01 Out', '02 Out', '03 Out', '04 Out', '05 Out', '06 Out', '07 Out'],
        'flow_created': [150, 141, 145, 152, 135, 125, 130],
        'flow_completed': [64, 41, 76, 41, 113, 173, 120],
        'tempo_etapas_categories': ['Triagem', 'Visita', 'Contrato', 'Fechamento'],
        'tempo_etapas_values': [1.1, 2.7, 1.9, 0.8],
        'distrib_categories': ['0-1d', '2-3d', '4-7d', '8+d'],
        'distrib_values': [10, 30, 40, 20],
    })