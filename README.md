
/api  a Python framework for solving the challenges

Requires Python version 3.11 if defaulting to an older version create a venv for the same
* python3.11 -m venv venv
* source venv/bin/activate

Challenge 1 : Echo
                bash session : source ./maelstrom/maelstrom test -w echo --bin ./maelstrom-echo/echo.py --node-count 1 --time-limit 10
                zsh session  : ./maelstrom/maelstrom test -w echo --bin ./maelstrom-echo/echo.py --node-count 1 --time-limit 10

Challenge 2 : Unique ID Generation
            
                Grant permission : chmod +x unique_id.py

                bash session : source ./maelstrom/maelstrom test -w unique-ids --bin ./maelstrom-unique-id/unique_id.py --time-limit 30 --rate 1000 --node-count 3 --availability total --nemesis partition
                zsh session : ./maelstrom/maelstrom test -w unique-ids --bin ./maelstrom-unique-id/unique_id.py --time-limit 30 --rate 1000 --node-count 3 --availability total --nemesis partition

Challenge 3 : Broadcast

            (3a)
                ./maelstrom/maelstrom test -w broadcast --bin ./maelstrom-broadcast/broadcast.py --node-count 1 --time-limit 20 --rate 10
            (3b)
                ./maelstrom/maelstrom test -w broadcast --bin ./maelstrom-broadcast/broadcast.py  --node-count 5 --time-limit 20 --rate 10
            (3c)
                ./maelstrom/maelstrom test -w broadcast --bin ./maelstrom-broadcast/broadcast.py --node-count 5 --time-limit 20 --rate 10 --nemesis partition
            (3d)
                ./maelstrom/maelstrom test -w broadcast --bin ./maelstrom-broadcast/broadcast.py --node-count 25 --time-limit 20 --rate 100 --latency 100
            (3e)
                ./maelstrom/maelstrom test -w broadcast --bin ./maelstrom-broadcast/broadcast.py  --node-count 25 --time-limit 20 --rate 100 --latency 100
