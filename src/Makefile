all: server.py
	@echo '#!/usr/bin/python3\n' > ../bin/serverExe
	@cat server.py >> ../bin/serverExe
	@chmod 777 ../bin/serverExe

clean:
	@rm -f ../bin/*
    