import hashlib                                  # hashlib  hash값에 관련한 library를 import
import json                                     # 쉽게 데이터를 교환하고 데이터를 저장하기 위하여 만들어진 텍스트 기반의 데이터 교환 표준
from time import time                           #
from urllib.parse import urlparse               # url 처리관련 라이브러리. 구문분석을 위한 parse
from uuid import uuid4                          # uuid 범용고유식별자 uuid4 랜덤넘버링

import requests
from flask import Flask, jsonify, request       #flask 파이썬의 웹프레임워크, 웹서버 구축 이용하는 외부모듈


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # Create the genesis block            # 초기블록 생성: 이전 해쉬값을 1로 정의하고 pof를 성립시킴.
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):         # 노드등록 함수.
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)         #parsed_url 값을 설정하는 구문. 주소를 받아서 해석함.
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):                  #주어진 체인의 길이가 가진 체인보다 길 경우 유효한지 검증하고 추가.
        """
        Determine if a given blockchain is valid

        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):       #주어진 체인의 길이가 자신이 가진 것 보다 길경우
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:   #이전해쉬가 마지막 해쉬와 다른 경우는 유효하지 않거나 더 긴 체인.
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):   #proof로 유효한지를 검증
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):                   #합의 알고리즘, 네트워크 상에서 가장 긴 체인(유효하고 최신)으로 바꾸는 작업
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:                                  #네트워크상 존재하는 모든 노드에 요청하여 검증
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):   #자신이 가진 블록의 갯수보다 많은가? 체인이 유효한가?
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:                               #새로운 체인을 대체함.
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):                     #새로운 블록 생성 함수
        """
        Create a new Block in the Blockchain

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,                                   # 인덱스+1
            'timestamp': time(),                                            # 시간기록
            'transactions': self.current_transactions,                      # 트랜잭션 기록
            'proof': proof,                                                 #proof
            'previous_hash': previous_hash or self.hash(self.chain[-1]),    # 이전해쉬나 샐프체인에 -1
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block                                                       #값을 다시 기록하면 블록에 넣음.

    def new_transaction(self, sender, recipient, amount):                   #트랜잭션 함수 보내는 사람, 받는 사람, amount 추가
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):                   #last block 함수는 self chain에 마지막 문자
        return self.chain[-1]

    @staticmethod
    def hash(block):                         #hash 블록 암호화를 return하는 함수.
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block):     #Pow 알고리즘, 진행하나가면서 더 긴 값을 찾아나가면서 값을 얻음.
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.

        """

        guess = f'{last_proof}{proof}{last_hash}'.encode() #데이터를 다른 곳으로 보내는 encode
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate the Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')              #랜덤넘버링으로 범용고유식별자 생성 후  -를 제거

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])                         #URL을 설정하고 /mine을 붙인 페이지에서 값을 받음
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])            #새로운 트랜잭션을 /transactions/news에 게시함.
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data  #트랜잭션을 올리기 전에 유효한지 확인, 아니면 400
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction                                # 값이 확인된 경우 트랜잭션을 생성함.
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])                  # /chain에서 지금까지의 체인을 받아옴.
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])        #/nodes/register에 유효한 node를 등록
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])    #주소에서 유효한 체인을 가져오는 것으로 최신의 체인으로
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser           #간단하게 argument를 파싱할 수 있게 하는 인자

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
