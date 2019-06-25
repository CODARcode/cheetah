campaign="gs"

create: 
	cheetah.py create-campaign -a . -o ${campaign} -e ${campaign}.py -m local
run:
	${campaign}/${USER}/run-all.sh
cancel:
	${campaign}/${USER}/Gray-Scott-A/cancel.sh
status:
	cheetah.py status ${campaign} -s
report:
	cheetah.py status ${campaign} -t -p
check0:
	cat gs/igor/Gray-Scott-A/run-0.iteration-0/pdf_calc/codar.workflow.stdout.pdf_calc
check1:
	cat gs/igor/Gray-Scott-A/run-1.iteration-0/pdf_calc/codar.workflow.stdout.pdf_calc
check2:
	cat gs/igor/Gray-Scott-A/run-2.iteration-0/pdf_calc/codar.workflow.stdout.pdf_calc
check3:
	cat gs/igor/Gray-Scott-A/run-3.iteration-0/pdf_calc/codar.workflow.stdout.pdf_calc


clean:
	rm -rf *~ ${campaign} __pycache__ 
