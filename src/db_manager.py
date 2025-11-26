import sqlite3
from typing import Optional

DATABASE_FILE = "sol2.db"

def get_db_connection():
    con = sqlite3.connect(DATABASE_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con

def init_db():
    with get_db_connection() as con:
        cursor = con.cursor()

        # 사용자 테이블
        cursor.execute('''  
        CREATE TABLE IF NOT EXISTS users (
            discord_id INTEGER PRIMARY KEY,
            solvedac_handle TEXT NOT NULL UNIQUE
        )
        ''')

        # 그룹 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT NOT NULL,
            server_id INTEGER,
            channel_id INTEGER,
            manager_id INTEGER NOT NULL,
            UNIQUE(server_id, group_name)
        )
        ''')

        # 그룹 멤버 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id INTEGER,
            group_id INTEGER,
            UNIQUE(discord_id, group_id),
            FOREIGN KEY (group_id) REFERENCES groups (group_id) ON DELETE CASCADE,
            FOREIGN KEY (discord_id) REFERENCES users (discord_id) ON DELETE CASCADE
        )
        ''')

        # 사용자 top100 문제 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_top100_problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solvedac_handle TEXT NOT NULL,
            problem_id INTEGER NOT NULL,
            UNIQUE (solvedac_handle, problem_id),
            FOREIGN KEY (solvedac_handle) REFERENCES users (solvedac_handle) ON DELETE CASCADE
        )
        ''')

        # 문제집 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS problem_sets (
            set_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            set_name TEXT,
            UNIQUE (group_id, set_name),
            FOREIGN KEY (group_id) REFERENCES groups (group_id) ON DELETE CASCADE
        )
        ''')

        # 문제집 문제 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS problem_set_problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER,
            problem_id INTEGER,
            FOREIGN KEY (set_id) REFERENCES problem_sets(set_id) ON DELETE CASCADE
        )
        ''')
        
		# 멤버가 푼 문제집 문제 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS member_solved_problems (
    		id INTEGER PRIMARY KEY AUTOINCREMENT,
    		member_id INTEGER NOT NULL,
    		problem_id INTEGER NOT NULL,
    		status TEXT DEFAULT 'solved',
    		FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    		FOREIGN KEY (problem_id) REFERENCES problem_set_problems(id) ON DELETE CASCADE,
    		UNIQUE(member_id, problem_id)
		)    
		''')
        
		# 라이벌 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rival (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
            my_id TEXT NOT NULL,
            rival_id TEXT NOT NULL,
            UNIQUE(my_id, rival_id),
            FOREIGN KEY (my_id) REFERENCES users(solvedac_handle) ON DELETE CASCADE,
            FOREIGN KEY (rival_id) REFERENCES users(solvedac_handle) ON DELETE CASCADE
        )
		''')

        
        con.commit()

# ==================== 사용자 테이블 관련 함수 ====================

# 사용자 등록
def register_user(discord_id: int, solvedac_handle: str) -> bool:
    with get_db_connection() as con:
        try:
            con.execute("INSERT OR IGNORE INTO users (discord_id, solvedac_handle) VALUES (?, ?)", (discord_id, solvedac_handle))
            con.commit()
            return True
        except Exception as e:
            print(f"register_user() Error: {e}")
            return False
        
def get_solvedac_handle(discord_id: int) -> Optional[str]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT solvedac_handle FROM users WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        return result['solvedac_handle'] if result else None
    
def is_user(solvedac_handle: str) -> bool:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT discord_id FROM users WHERE solvedac_handle = ?", (solvedac_handle,))
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False
        
def is_registered_user(discord_id: int) -> bool:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False
        
def get_users_for_update() -> list:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT solvedac_handle FROM users")
        result = cursor.fetchall()
        return [row['solvedac_handle'] for row in result]
    
# ==================== 그룹 테이블 관련 함수 ====================

def create_group(group_name: str, server_id: int|None, channel_id: int|None, manager_id: int) -> bool:
    with get_db_connection() as con:
        try:
            con.execute("INSERT INTO groups (group_name, server_id, channel_id, manager_id) VALUES (?, ?, ?, ?)", (group_name, server_id, channel_id, manager_id))
            con.commit()
            return True
        except Exception as e:
            print(f"create_group() Error: {e}")
            return False

def delete_group(group_name: str, manager_id: int) -> bool:
    with get_db_connection() as con:
        try:
            cur = con.execute("DELETE FROM groups WHERE group_name = ? AND manager_id = ?", (group_name, manager_id))
            con.commit()
            return cur.rowcount > 0
        except Exception as e:
            print(f"delete_group() Error: {e}")
            return False

def get_group_id(server_id: int|None, channel_id: int|None) -> Optional[int]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT group_id FROM groups WHERE server_id = ? AND channel_id = ?", (server_id, channel_id))
        result = cursor.fetchone()
        return result['group_id'] if result else None
    
def get_group_name(group_id:int) -> Optional[str]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT group_name FROM groups WHERE group_id = ?", (group_id,))
        result = cursor.fetchone()
        return result['group_name'] if result else None

def get_group_manager(group_id: int) -> Optional[int]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT manager_id FROM groups WHERE group_id = ?", (group_id,))
        result = cursor.fetchone()
        if result:
            return result['manager_id']
        return None

def get_channel_id(group_id: int) -> Optional[int]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT channel_id FROM groups WHERE group_id = ?", (group_id,))
        result = cursor.fetchone()
        if result:
            return result['channel_id']
        return None

# ==================== 그룹 멤버 관련 함수 ====================

def add_group_member(discord_id: int, solvedac_handle: str, group_id: int|None) -> bool:
    try:
        register_user(discord_id, solvedac_handle)
        with get_db_connection() as con:
            con.execute("INSERT INTO members (discord_id, group_id) VALUES (?, ?)", (discord_id, group_id))
            con.commit()
            return True
    except sqlite3.IntegrityError:
        print("Member already in group or invalid ID")
        return False
    except Exception as e:
        print(f"add_group_member() Error: {e}")
        return False

def delete_member(discord_id: int, group_id: int|None) -> bool:
    with get_db_connection() as con:
        try:
            cur = con.execute("DELETE FROM members WHERE discord_id = ? AND group_id = ?", (discord_id, group_id))
            con.commit()
            return cur.rowcount > 0
        except Exception as e:
            print(f"delete_member() Error: {e}")
            return False    

def get_member(group_id: int) -> Optional[list]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT discord_id FROM members WHERE group_id = ?", (group_id,))
        result = cursor.fetchall()
        return [row['discord_id'] for row in result] if result else None
    
def is_member(solvedac_handle: str, group_id: int|None) -> bool:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("""
            SELECT 1
            FROM users u
            JOIN members m ON u.discord_id = m.discord_id
            WHERE u.solvedac_handle = ? AND m.group_id = ?
        """, (solvedac_handle, group_id))
        return cursor.fetchone() is not None

# ==================== 사용자 top100 문제 테이블 관련 함수 ====================

def insert_user_top100(solvedac_handle: str, problem_ids: list):
    problem_set_ids = set(problem_ids)
    with get_db_connection() as con:
        insert_data = [(solvedac_handle, pid) for pid in problem_set_ids]
        con.executemany("INSERT INTO user_top100_problems (solvedac_handle, problem_id) VALUES (?, ?)", insert_data)
        con.commit()

def get_user_top100(solvedac_handle: str) -> list:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT problem_id FROM user_top100_problems WHERE solvedac_handle = ?", (solvedac_handle,))
        result = cursor.fetchall()
        return [row['problem_id'] for row in result]
  
def update_user_top100(solvedac_handle: str, new_problem_ids: list) -> list:
    new_problem_set = set(new_problem_ids)
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT problem_id FROM user_top100_problems WHERE solvedac_handle = ?", (solvedac_handle,))
        old_result = cursor.fetchall()
        old_problem_set = set(row['problem_id'] for row in old_result)

        newly_added_problems = list(new_problem_set - old_problem_set)
        
        if newly_added_problems:
            insert_data = [(solvedac_handle, pid) for pid in newly_added_problems]
            cursor.executemany("INSERT INTO user_top100_problems (solvedac_handle, problem_id) VALUES (?, ?)", insert_data)
        
        con.commit()
        return newly_added_problems

# ==================== 문제집 테이블 관련 함수 ====================

def create_problem_set(group_id: int, set_name: str) -> bool:
    with get_db_connection() as con:
        try: 
            con.execute("INSERT INTO problem_sets (group_id, set_name) VALUES (?, ?)", (group_id, set_name))
            con.commit()
            return True
        except Exception as e:
            print(f"Error create_problem_set: {e}")
            return False

def delete_problem_set(group_id: int, set_name: str) -> bool:
    with get_db_connection() as con:
        cur = con.execute("DELETE FROM problem_sets WHERE group_id = ? AND set_name = ?", (group_id, set_name))
        con.commit()
        return cur.rowcount > 0

def get_problem_set(group_id: int) -> Optional[list]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT set_name FROM problem_sets WHERE group_id = ?", (group_id,))
        result = cursor.fetchall()
        return [row['set_name'] for row in result] if result else None
    
def get_set_id(group_id: int, set_name: str) -> Optional[int]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT set_id FROM problem_sets WHERE group_id = ? AND set_name = ?", (group_id, set_name))
        result = cursor.fetchone()
        return result['set_id'] if result else None

# ==================== 문제집 문제 테이블 관련 함수 ====================

def add_problem(set_id: int, problem_id: int):
    with get_db_connection() as con:
        con.execute("INSERT INTO problem_set_problems (set_id, problem_id) VALUES (?, ?)", (set_id, problem_id))
        con.commit()

def delete_problem(set_id: int, problem_id: int):
    with get_db_connection() as con:
        con.execute("DELETE FROM problem_set_problems WHERE set_id = ? AND problem_id = ?", (set_id, problem_id))
        con.commit()

def get_problem(set_id: int) -> Optional[list]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT problem_id FROM problem_set_problems WHERE set_id = ?", (set_id,))
        result = cursor.fetchall()
        return [row['problem_id'] for row in result] if result else None
    
# ==================== 멤버가 푼 문제집 문제 테이블 ====================

# ==================== 라이벌 테이블 관련 함수 ====================

def make_rival(my_id: str, rival_id: str):
    with get_db_connection() as con:
        con.execute("INSERT INTO rival (my_id, rival_id) VALUES (?, ?)", (my_id, rival_id))
        con.commit()
        
def erase_rival(my_id:str, rival_id:str):
    with get_db_connection() as con:
        con.execute("DELETE FROM rival WHERE my_id = ? AND rival_id = ?", (my_id, rival_id))
        con.commit()
        
def get_rival(my_id: str) -> Optional[list]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT rival_id FROM rival WHERE my_id = ?", (my_id,))
        result = cursor.fetchall()
        return [row['rival_id'] for row in result] if result else None
        
def get_reverse_rival(my_id:str) -> Optional[list]:
    with get_db_connection() as con:
        cursor = con.cursor()
        cursor.execute("SELECT my_id FROM rival WHERE rival_id = ?", (my_id,))
        result = cursor.fetchall()
        return [row['my_id'] for row in result] if result else None