from django.shortcuts import render, redirect, get_object_or_404
from .models import Staff
from .forms import StaffForm
from django.urls import reverse
from django.http import JsonResponse

def user_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save()
            return JsonResponse({'success': True, 'id': staff.id, 'name': str(staff)})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False, 'message': 'Only POST allowed'}, status=405)

def user_list(request):
    qs = Staff.objects.all().order_by('last_name', 'first_name')
    return render(request, 'users/user_list.html', {'staff_list': qs})

def user_add(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = StaffForm()
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Add'})

def user_edit(request, pk):
    obj = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = StaffForm(instance=obj)
    return render(request, 'users/user_form.html', {'form': form, 'action': 'Edit', 'staff': obj})

def user_delete(request, pk):
    obj = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        obj.delete()
        return redirect('user_list')
    return render(request, 'users/user_confirm_delete.html', {'staff': obj})

