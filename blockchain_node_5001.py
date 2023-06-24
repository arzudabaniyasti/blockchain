#create blockchain and cryptocurrency
import datetime 
import hashlib #kriptogrofik hash fonksiyonu kullancaz.
import json 
from flask import Flask, jsonify, request
import requests 
#merkezi olmayan blok zincirindeki tüm düğümlerin gerçektend de aynı düğüme sahip mi değil mi kontrolü yapcaz.
from uuid import uuid4
from urllib.parse import urlparse
import math


class Blockchain:
    def __init__(self):
        self.chain = [] #blockları içeren bir list
        #en başta işlemler bir blok halinde değildir. bir madenci blok çıkardığı anda biriken tüm işlemler bloğa eklenir. blok oluşturma işleminden önce olması lazım.
        self.transactions = [] #işlem listesi.
        self.markets = {}
        self.b = 3
        self.create_block(proof = 1, previous_hash = '0')
        self.nodes = set()#sırası olmadığı için array. 
        
    def create_block(self, proof, previous_hash):
        block = {'index' : len(self.chain) + 1,
                 'timestamp' : str(datetime.datetime.now()),
                 'proof' : proof,
                 'previous_hash' : previous_hash,
                 'transactions' : self.transactions,
                 'markets': self.markets}
        self.transactions = [] 
        #başka blocka geçtiğinde bu listenin boşaltılması gerek.
        self.chain.append(block)
        return block
    
    def get_previous_block(self):
        return self.chain[-1] #last block of the chain

    
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation =  hashlib.sha256(str(new_proof*2-previous_proof*2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof
    
    #hash function
    def hash(self, block):
        encoded_block = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1 
        while block_index < len(chain):
            block = chain[block_index]#mevcut blok
            if block['previous_hash'] != self.hash(previous_block):
                return False 
            previous_proof = previous_block['proof']
            proof = block['proof'] #current block proof
            hash_operation =  hashlib.sha256(str(proof*2-previous_proof*2).encode()).hexdigest()
            if hash_operation[:4] !='0000':
                return False
            previous_block = block
            block_index +=1
        return True
    
    def add_transactions(self, sender, receiver, amount):
        self.transactions.append({'sender' : sender, 
                                  'receiver' : receiver,
                                  'amount' : amount})
        #return yapmamız gereken şey index of the block that will receive this transactions.
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1
    
    def create_market(self, market_name, stocks, closing_date):
        self.markets[market_name] = {'stocks': {stock: {'price': 1, 'investors': []} for stock in stocks},
                                 'closing_date': closing_date}
        
    def add_investment(self, market_name, stock, investor, amount):
        self.markets[market_name]['stocks'][stock]['investors'].append((investor, amount))
        self.update_prices(market_name)

    def update_prices(self, market_name):
        total_transactions = sum([stock_info['investors'][-1][1] for stock_info in self.markets[market_name]['stocks'].values() if stock_info['investors']])  # Get the total transactions only if the investors list is not empty
        total_value = sum([stock_info['price'] for stock_info in self.markets[market_name]['stocks'].values()])  # Get the total value
        for stock, stock_info in self.markets[market_name]['stocks'].items():
            if stock_info['investors']:  # If the investors list is not empty
                self.calculate_stock_ratio(stock_info, total_transactions, self.b)
                stock_info['price'] = total_value * stock_info['ratio']

    def calculate_stock_ratio(self, stock_info, total_transactions, b):
        stock_transactions = stock_info['investors'][-1][1]  # Get the total transactions for the stock
        ratio = (1 / b) * math.log(math.exp(b * stock_transactions) / total_transactions)
        stock_info['ratio'] = ratio

    # Add new function to close market and distribute rewards
    def close_market(self, market_name, winning_stock):
        market = self.markets[market_name]
        for investor, amount in market['stocks'][winning_stock]['investors']:
            investor.balance += market['stocks'][winning_stock]['price'] * amount  # Update balance according to the final price
            
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
        
    #şimdi ise ağın tüm düğümleri arasında en uzun zincirden daha kısa olan bir zincir varsa değiştricek olan methodu yazalım.
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
                    markets = response.json()['markets'] # Get the markets from the node
        if longest_chain:
            self.chain = longest_chain
            self.markets = markets  # Update the markets in the current node
            return True
        return False

#create a web app
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

#creating an address fotr the node on Port 5000
node_address = str(uuid4()).replace('-','') #♦bir id üretiyor arasındaki tireleri çıkardık.

#creating blockchain
blockchain = Blockchain()

#mining a new block
@app.route('/mine_block',methods = ['GET'])
def mine_block():
    #how do we mine a block? öncelikle proof of wrok problemini çözmemiz gerekiyor proofu  bularak.
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    blockchain.add_transactions(sender=node_address, receiver='arzu', amount = 10)#miner mine yapınca coin kazanacak.
    #create yapmak için previous hasha ihtiyaç var
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)
    response = {'message': 'Congratulations, you just mined a block!',
                'index' : block['index'],
                'timestamp' : block['timestamp'],
                'proof' : block['proof'],
                'previous_hash' : block['previous_hash'],
                'transactions' : block['transactions']}
    return jsonify(response),200

@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
        'markets': blockchain.markets
    }
    return jsonify(response), 200

#check blockchain
@app.route('/is_valid',methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': "The Blokchain is valid"}
    else:
        response = {'message' : "The Blokchain is not valid"}
    return jsonify(response),200

#add new transaction to te blockchain
@app.route('/add_transaction',methods = ['POST'])
def add_transaction():
    #postmandaki json dosyasından receiver,sender ve amount kullancaz
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all (key in json for key in transaction_keys):
        return 'some elements of the transactions are missing', 400
    index = blockchain.add_transactions(json['sender'],json['receiver'],json['amount'])
    response = {'message' : f'This transaction will be added to Block {index}' }
    return jsonify(response),201

@app.route('/connect_node',methods = ['POST'])
def connect_node():
    json = request.get_json()
    #bir düğümü ağdaki diğer düğümlere bağlamak gerekiyor.
    nodes = json.get('nodes')
    #json={"nodes":["127.0.0.0:5000",....]}
    if nodes is None:
        return "No Nodes",400
    #adresler üzerinde döngü ypıp eklicesz.
    for node in nodes:
        blockchain.add_node(node)
    response = {'message' : 'All the nodes are connected. This Blokchain contains the following nodes:',
                'total_nodes' : list(blockchain.nodes) }
    return jsonify(response),201

#replacing chain by the longest chain if needed. get isteği.
@app.route('/replace_chain',methods = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': "The Chain is replaced",
                    'new_chain' : blockchain.chain}
    else:
        response = {'message' : "The Chain is not replaced. Chain is already largest one",
                    'actual_chain' : blockchain.chain}
    return jsonify(response),200

@app.route('/create_market', methods=['POST'])
def create_market():
    json = request.get_json()
    market_keys = ['market_name', 'stocks', 'closing_date']
    if not all (key in json for key in market_keys):
        return 'Some elements of the market are missing', 400
    blockchain.create_market(json['market_name'], json['stocks'], json['closing_date'])
    response = {'message': f'Market {json["market_name"]} has been created'}
    return jsonify(response), 201

@app.route('/add_investment', methods=['POST'])
def add_investment():
    json = request.get_json()
    # Remove 'investor' from keys
    investment_keys = ['market_name', 'stock', 'amount']
    if not all (key in json for key in investment_keys):
        return 'Some elements of the investment are missing', 400
    # Use node_address as investor
    blockchain.add_investment(json['market_name'], json['stock'], node_address, json['amount'])
    response = {'message': f'{node_address} has invested in {json["stock"]} from {json["market_name"]}'}
    return jsonify(response), 201

@app.route('/close_market', methods=['POST'])
def close_market():
    json = request.get_json()
    close_keys = ['market_name', 'winning_stock']
    if not all (key in json for key in close_keys):
        return 'Some elements of the market closing are missing', 400
    blockchain.close_market(json['market_name'], json['winning_stock'])
    response = {'message': f'Market {json["market_name"]} has been closed with {json["winning_stock"]} as the winning stock'}
    return jsonify(response), 201

#run the app
app.run(host = '0.0.0.0', port = 5001)