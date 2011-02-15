PROGRAM = dbus-yum-test
PROGRAM_FILES = dbus-yum-test.c

CC      = gcc
CFLAGS	+= -g $(shell pkg-config --cflags glib-2.0 dbus-glib-1)
LDFLAGS	+= -g
LIBS 	+= $(shell pkg-config --libs glib-2.0 dbus-glib-1) 

all: $(PROGRAM)

%: %.c 
	$(CC) $(PROGRAM_FILES) $(CFLAGS) $(LDFLAGS) -o $(PROGRAM) $(LIBS)

clean:
	@rm -rf $(PROGRAM)
		    
