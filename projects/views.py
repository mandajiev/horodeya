from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic
from django.utils import timezone


from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from projects.models import Project

#from .models import Проект

#class IndexView(generic.ListView):
#    template_name = 'проекти/index.html'
#    context_object_name = 'последни_проекти'
#
#    def get_queryset(self):
#        """Return the last five published questions."""
#        return Проект.objects.filter(
#                публикуване__lte=timezone.now()
#        ).order_by('-публикуване')[:5]
#
class Details(generic.DetailView):
    model = Project
#
##
##class ResultsView(generic.DetailView):
##    model = Question
##    template_name = 'polls/results.html'
##
##def vote(request, question_id):
##    question = get_object_or_404(Question, pk=question_id)
##    try:
##        selected_choice = question.choice_set.get(pk=request.POST['choice'])
##    except (KeyError, Choice.DoesNotExist):
##        # Redisplay the question voting form.
##        return render(request, 'polls/detail.html', {
##            'question': question,
##            'error_message': "You didn't select a choice.",
##        })
##    else:
##        selected_choice.votes += 1
##        selected_choice.save()
##        # Always return an HttpResponseRedirect after successfully dealing
##        # with POST data. This prevents data from being posted twice if a
##        # user hits the Back button.
##        return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))

class ProjectCreate(CreateView):
    model = Project
    fields = ['type', 'name', 'description', 'published' , 'legal_entity']

class ProjectUpdate(UpdateView):
    model = Project
    fields = ['type', 'name', 'description', 'published', 'legal_entity' ]

class ProjectDelete(DeleteView):
    model = Project
    success_url = '/'

#    def form_valid(self, form):
#        #TODO
#        return super().form_valid(form)
