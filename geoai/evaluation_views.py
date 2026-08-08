from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .evaluation_services import build_evaluation_dashboard
from .kfold_services import load_kfold_result, run_stratified_kfold


@login_required
def system_evaluation(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Faqat superadministrator uchun')
    context=build_evaluation_dashboard()
    context['kfold']=load_kfold_result()
    return render(request,'geoai/system_evaluation.html',context)


@login_required
@require_POST
def run_kfold(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    try:
        folds=int(request.POST.get('folds','5'))
        if folds not in (5,10): folds=5
        result=run_stratified_kfold(folds)
        messages.success(request,f"{folds}-Fold tekshiruv yakunlandi. Accuracy={result['accuracy']['mean']:.3f} ± {result['accuracy']['std']:.3f}")
    except Exception as exc:
        messages.error(request,f'K-Fold bajarilmadi: {exc}')
    return redirect('geoai:system_evaluation')
