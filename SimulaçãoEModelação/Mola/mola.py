"""
Movimento Oscilatório Composto - Gonçalo Baptista, nº 55069; José Grilo, nº 54926

Objetivo de Programação:
"""
#%%

%matplotlib qt
import numpy as np
import matplotlib.pyplot as plt
import scipy.fft as sc
import matplotlib.animation as animation
import copy
from matplotlib.widgets import Slider, Button, RangeSlider, TextBox, CheckButtons, RadioButtons
import sys
import time as ti

#%%

class Body:                 #   Cada corpo possui associado a si uma mola à esquerda
    def __init__(self, mass, k, xEq, x0, v0, size):
        self.mass = mass    #   Massa do corpo
        self.k = k          #   Constante de mola associada ao corpo
        self.xEq = xEq      #   Distância de equilíbrio da mola associada ao corpo
        self.x = x0         #   Posição instantânea
        self.v = v0         #   Velocidade instantânea
        
        self.xList = np.zeros(size) # Vetor da amostragens das posições
        self.vList = np.zeros(size) # Vetor da amostragens das velocidades
        
        self.xList[0] = x0          # Guarda-se a posição inicial
        self.vList[0] = v0          # Guarda-se a posição inicial
        
   
#%%

def initSimul(Tmax, dt, tSample, sArray, alg = 'CromerRK4'):
    
    size = int(Tmax/tSample)    # Calcula o número de amostragens que serão feitas
    saveSteps = int(tSample/dt) # Calcula o número de passos realizados até ocorrer amostragem
    n = len(sArray)             # Número de corpos/molas no sistema
    
    springs = np.zeros(n, dtype = object) # Inicializa o array que vai conter os objetos
    sForce = np.zeros(n + 1, dtype = float) # Inicializa o array que irá conter as forças exercidas por cada mola
    sAcce = np.zeros(n, dtype = float) # Inicializa o array que irá conter as acelerações sentidas por cada corpo
    sAcce1 = np.zeros(n, dtype = float)
    sAcce2 = np.zeros(n, dtype = float)
    xLast = np.zeros(n, dtype = float)
    xPos = np.zeros(n, dtype = float)
    time = np.zeros(size + 1, dtype = float) # Inicializa o array que irá conter o tempo de cada amostragem. Será útil nas FFTs.
    energy = np.zeros(size + 1, dtype = float) # Inicializa o array que irá conter as energias do sistema a cada amostragem.
    
    if alg == 'Verlet':
        return size, saveSteps, n, springs, sForce, sAcce, time, energy, xLast, xPos
    elif alg == 'Beeman':
        return size, saveSteps, n, springs, sForce, sAcce, sAcce1, sAcce2, time, energy
    else:
        return size, saveSteps, n, springs, sForce, sAcce, time, energy
    

#%%

def energyCalc(springs):
    """
    Função
    ---------
    Calcula a soma das energias potenciais das molas e cinéticas dos corpos

    Parameters
    ----------
    springs : Array de objetos
        Array onde tem as várias molas/corpos do sistema

    Returns
    -------
    energy : float
        Energia total do sistema.
    """
    n = springs.size
    energy = 0
    
    for i in range(n):
        if i == 0: # Neste caso na mola da esquerda, a posição do corpo já é a distância total.
            energy += 0.5 * springs[i].mass * springs[i].v ** 2 + 0.5 * springs[i].k * (springs[i].x - springs[i].xEq) ** 2
        else:               
            energy += 0.5 * springs[i].mass * springs[i].v ** 2 + 0.5 * springs[i].k * (springs[i].x - springs[i - 1].x - springs[i].xEq) ** 2
    
    return energy
        
#%%
        
def acceCalc(springs, sSize, sForce, sAcce): 
    """
    Função:
    ---------
    Calcula as forças e acelerações para todos os corpos do sistema.
    
    Parameters
    ----------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    sSize : Int
        Indicador do número de molas/corpos
    sForce : Array de floats
        Array de Forças sentidas exercidas pelo corpo da esquerda
    sAcce : Array de floats
        Array com as acelerações sentidas por cada corpo. Necessário para o cálculo do próximo passo
        
    Returns
    -------
    Não retorna nada. Apenas modifica Arrays já existentes.
    """
    for i in range(sSize): # Calcula-se a força que cada mola está a exercer
        if i == 0:
            sForce[i] = springs[i].k * (springs[i].x - springs[i].xEq)
        else:
            sForce[i] = springs[i].k * (springs[i].x - springs[i - 1].x - springs[i].xEq)
            
    for i in range(sSize): # Somam-se as forças da mola da esquerda e da direita para cada corpo e calcula-se a aceleração dividindo pela massa do corpo
        sAcce[i] = - sForce[i] / springs[i].mass + sForce[i + 1] / springs[i].mass
        
#%%
        
def acceCalcRK4(springs, sSize, sForce, sAcce, dx):
    """
    Função:
    ---------
    Calcula as forças e acelerações para todos os corpos do sistema nos passos intermédios do RK4

    Parameters
    ----------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    sSize : Int
        Indicador do número de molas/corpos
    sForce : Array de floats
        Array de Forças sentidas exercidas pelo corpo da esquerda
    sAcce : Array de floats
        Array com as acelerações sentidas por cada corpo. Necessário para o cálculo do próximo passo
    dx : Array de floats
        Array com os deslocamentos adicionais para cada corpo usados no cálculo das acelerações intermédias no RK4

    Returns
    -------
    Nada. Atualiza o array das acelerações
    """
    for i in range(sSize):
        if i == 0:
            sForce[i] = springs[i].k * (springs[i].x + dx[i] - springs[i].xEq)
        else:
            sForce[i] = springs[i].k * (springs[i].x + dx[i] - springs[i - 1].x - dx[i-1] - springs[i].xEq)
            
    for i in range(sSize):
        sAcce[i] = - sForce[i] / springs[i].mass + sForce[i + 1] / springs[i].mass 

#%%

def springCalcCromer(springs, sForce, sAcce, saveSteps, dt):
    """
    Função:
    ---------
    Calcula as novas posições e velocidades para cada mola com base no algoritmo de Euler-Cromer

    Parameters
    ----------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    sForce : Array de floats
        Array de Forças sentidas exercidas pelo corpo da esquerda
    sAcce : Array de floats
        Array com as acelerações sentidas por cada corpo. Necessário para o cálculo do próximo passo
    saveSteps : Int
        Número de passos que devem ser executados até se guardar os dados para amostragem.
    dt : float
        Tempo entre passos

    Returns
    -------
    Nada. Apenas atualiza as coordenadas e velocidades instantâneas para cada corpo.
    """
    n = springs.size
    passo = 0
    
    while passo < saveSteps: # executa várias iterações e atualiza as posições e velocidades instantâneas até ser necessário recolher amostragem
        acceCalc(springs, n, sForce, sAcce)
        for i in range(n):
            springs[i].v += sAcce[i] * dt
            springs[i].x += springs[i].v * dt
        passo += 1

#%%        
        
def springCalcVerlet(springs, sForce, sAcce, saveSteps, dt, xLast, xPos):
    """
    Função:
    ---------
    Calcula as novas posições e velocidades para cada mola com base no algoritmo de Verlet

    Parameters
    ----------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    sForce : Array de floats
        Array de Forças sentidas exercidas pelo corpo da esquerda
    sAcce : Array de floats
        Array com as acelerações sentidas por cada corpo. Necessário para o cálculo do próximo passo
    saveSteps : Int
        Número de passos que devem ser executados até se guardar os dados para amostragem.
    dt : float
        Tempo entre passos
    xLast : Array de floats
        Posição do passo anterior para cada corpo.
    xPos : Array de floats
        Posição atual para cada corpo

    Returns
    -------
    xLast : Array de floats
        Posição do passo anterior para cada corpo.
    """
    n = springs.size
    passo = 0
    
    while passo < saveSteps:
        acceCalc(springs, n, sForce, sAcce) # Atualiza a nova aceleração
        for i in range(n):
            xPos[i] = copy.deepcopy(springs[i].x) # Atualiza a posição atual
            springs[i].x = 2 * springs[i].x - xLast[i] + sAcce[i] * dt ** 2 # Calcula a nova posição segundo o método de Verlet
            springs[i].v = (springs[i].x - xLast[i]) / (2 * dt) # Calcula a nova velocidade segundo o método de Verlet

        xLast = copy.deepcopy(xPos) # Atualiza a posição anterior
        passo += 1
        
    return xLast

#%%

def springCalcBeeman(springs, sForce, sAcce0, sAcce1, sAcce2, saveSteps, dt):
    """
    Função:
    ---------
    Calcula as novas posições e velocidades para cada mola com base no algoritmo de Beeman

    Parameters
    ----------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    sForce : Array de floats
        Array de Forças sentidas exercidas pelo corpo da esquerda.
    sAcce0 : Array de floats
        Array com as acelerações do passo anterior
    sAcce1 : Array de floats
        Array com as acelerações  do passo atual
    sAcce2 : Array de floats
        Array com as acelerações do próximo passo
    saveSteps : Int
        Número de passos que devem ser executados até se guardar os dados para amostragem.
    dt : float
        Tempo entre passos

    Returns
    -------
    sAcce0 : Array de floats
        Array com as acelerações do passo anterior
    sAcce1 : Array de floats
        Array com as acelerações  do passo atual
    sAcce2 : Array de floats
        Array com as acelerações do próximo passo
    """
    n = springs.size
    passo = 0
    
    while passo < saveSteps: 
        for i in range(n):
            springs[i].x += springs[i].v * dt + 2/3 * sAcce1[i] * dt ** 2 - 1/6 * sAcce0[i] * dt ** 2 # Cálculo das posições segundo o método de Beeman
        acceCalc(springs, n, sForce, sAcce2) # Atualiza a nova aceleração
        for i in range(n):
            springs[i].v += 1/3 * sAcce2[i] * dt + 5/6 * sAcce1[i] * dt - 1/6 * sAcce0[i] * dt     # Cálculo das velocidades segundo o método de Beeman

        sAcce0 = copy.deepcopy(sAcce1)  # Atualiza a aceleração anterior
        sAcce1 = copy.deepcopy(sAcce2)  # Atualiza a aceleração atual
        
        passo += 1
        
    return sAcce0, sAcce1, sAcce2
       
#%%

def springCalcRK4(springs, sForce, sAcce, saveSteps, dt):
    """
    Função:
    ---------
    Calcula as novas posições e velocidades para cada mola com base no algoritmo de Runge-Kutta de Ordem 4

    Parameters
    ----------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    sForce : Array de floats
        Array de Forças sentidas exercidas pelo corpo da esquerda
    sAcce : Array de floats
        Array com as acelerações sentidas por cada corpo. Necessário para o cálculo do próximo passo
    saveSteps : Int
        Número de passos que devem ser executados até se guardar os dados para amostragem.
    dt : float
        Tempo entre passos

    Returns
    -------
    Nada. Apenas atualiza as coordenadas e velocidades instantâneas para cada corpo
    """
    n = springs.size
    passo = 0
    sForceRK = np.zeros(n + 1, dtype = float) #Array que guarda as forças de cada mola durante os passos intermédios do algoritmo
    sAcceRK = np.zeros(n, dtype = float) #Array que guarda as acelerações de cada corpo durante os passos intermédios do algoritmo
    x1 = np.zeros(n)  # Array dos dx1
    v1 = np.zeros(n)  # Array dos dv1
    x2 = np.zeros(n)  # Array dos dx2
    v2 = np.zeros(n)  # Array dos dv2
    x3 = np.zeros(n)  # Array dos dx3
    v3 = np.zeros(n)  # Array dos dv3
    x4 = np.zeros(n)  # Array dos dx4
    v4 = np.zeros(n)  # Array dos dv4
    
    while passo < saveSteps:
        acceCalc(springs, n, sForce, sAcce)
        
        for i in range(n):  # Calcula os dx e dv da 1a iteração RK
            x1[i] = dt * springs[i].v
            v1[i] = sAcce[i] * dt
        
        acceCalcRK4(springs, n, sForceRK, sAcceRK, x1/2) # Calcula a nova aceleração intermédia
        for i in range(n):  # Calcula os dx e dv da 2a iteração RK
            x2[i] = dt * (springs[i].v + v1[i]/2)
            v2[i] = sAcceRK[i] * dt
            
        acceCalcRK4(springs, n, sForceRK, sAcceRK, x2/2) # Calcula a nova aceleração intermédia
        for i in range(n):  # Calcula os dx e dv da 3a iteração RK
            x3[i] = dt * (springs[i].v + v2[i]/2)
            v3[i] = sAcceRK[i] * dt
    
        acceCalcRK4(springs, n, sForceRK, sAcceRK, x3)   # Calcula a nova aceleração intermédia
        for i in range(n):  # Calcula os dx e dv da 4a iteração RK
            x4[i] = dt * (springs[i].v + v3[i])
            v4[i] = sAcceRK[i] * dt
         
        for i in range(n):  # Calcula e atualiza para cada mola a nova velocidade e posição da nova iteração
            springs[i].v += 1/6 * (v1[i] + 2 * v2[i] + 2 * v3[i] + v4[i])
            springs[i].x += 1/6 * (x1[i] + 2 * x2[i] + 2 * x3[i] + x4[i])
            
        passo += 1

#%%

def springSimulCromer(Tmax, dt, tSample, sArray):
    """
    Função:
    ---------
    Executa a simulação segundo o algoritmo de Euler-Cromer

    Parameters
    ----------
    Tmax : Float
        Tempo total da simulação
    dt : Float
        Tempo entre passos
    tSample : Float
        Tempo entre cada amostragem
    sArray : Array de strings
        Array com as características de inicialização de cada corpo indicadas pelo usuário na GUI.

    Returns
    -------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    energy : Array de floats
        Array com as energias do sistema a cada amostragem
    time : Array de floats
        Array com os tempos de cada amostragem
    """
    t0 = ti.time()
    size, saveSteps, n, springs, sForce, sAcce, time, energy = initSimul(Tmax, dt, tSample, sArray)
    
    for i in range(n):
        springs[i] = Body(sArray[i][0], sArray[i][1], sArray[i][2], sArray[i][3], sArray[i][4], size + 1) # Cria os objetos com as características de cada corpo/mola especificadas pelo utilizador na GUI
    
    energy[0] = energyCalc(springs) # Adiciona a energia do sistema no estado inicial
    
    for i in range(size): # Executa todas as amostragens
        time[i + 1] = time[i] + tSample # Adiciona o tempo da nova amostragem
        springCalcCromer(springs, sForce, sAcce, saveSteps, dt) # Executa o cálculo de várias iterações até ocorrer amostragem segundo o algorítmo de Euler-Cromer
        for j in range(n):
            springs[j].vList[i + 1] = springs[j].v # Guarda o valor atual da velocidade
            springs[j].xList[i + 1] = springs[j].x # Guarda o valor atual da posição
        energy[i + 1] = energyCalc(springs)
        
    t1 = ti.time()
    print('Euler-Cromer time: ' + str(t1 - t0))
        
    return springs, energy, time

#%%

def springSimulVerlet(Tmax, dt, tSample, sArray):
    """
    Função:
    ---------
    Executa a simulação segundo o algoritmo de Verlet

    Parameters
    ----------
    Tmax : Float
        Tempo total da simulação
    dt : Float
        Tempo entre passos
    tSample : Float
        Tempo entre cada amostragem
    sArray : Array de strings
        Array com as características de inicialização de cada corpo indicadas pelo usuário na GUI.

    Returns
    -------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    energy : Array de floats
        Array com as energias do sistema a cada amostragem
    time : Array de floats
        Array com os tempos de cada amostragem
    """
    t0 = ti.time()   
    size, saveSteps, n, springs, sForce, sAcce, time, energy, xLast, xPos = initSimul(Tmax, dt, tSample, sArray, alg = 'Verlet')
    
    for i in range(n):
        springs[i] = Body(sArray[i][0], sArray[i][1], sArray[i][2], sArray[i][3], sArray[i][4], size + 1)
        xLast[i] = springs[i].x - springs[i].v * dt
    
    energy[0] = energyCalc(springs)
    
    for i in range(size):
        time[i + 1] = time[i] + tSample
        xLast = springCalcVerlet(springs, sForce, sAcce, saveSteps, dt, xLast, xPos)
            
        for j in range(n):
            springs[j].vList[i + 1] = springs[j].v
            springs[j].xList[i + 1] = springs[j].x
        energy[i + 1] = energyCalc(springs)
        
    t1 = ti.time()
    print('Verlet time: ' + str(t1 - t0))
        
    return springs, energy, time

#%%

def springSimulBeeman(Tmax, dt, tSample, sArray):
    """
    Função:
    ---------
    Executa a simulação segundo o algoritmo de Beeman

    Parameters
    ----------
    Tmax : Float
        Tempo total da simulação
    dt : Float
        Tempo entre passos
    tSample : Float
        Tempo entre cada amostragem
    sArray : Array de strings
        Array com as características de inicialização de cada corpo indicadas pelo usuário na GUI.

    Returns
    -------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    energy : Array de floats
        Array com as energias do sistema a cada amostragem
    time : Array de floats
        Array com os tempos de cada amostragem
    """
    t0 = ti.time()
    size, saveSteps, n, springs, sForce, sAcce0, sAcce1, sAcce2, time, energy = initSimul(Tmax, dt, tSample, sArray, alg = 'Beeman')
    
    for i in range(n):
        springs[i] = Body(sArray[i][0], sArray[i][1], sArray[i][2], sArray[i][3], sArray[i][4], size + 1)
    
    energy[0] = energyCalc(springs)
    
    for i in range(size):
        if i == 0 :
            acceCalc(springs, n, sForce, sAcce1)
            sAcce0 = copy.deepcopy(sAcce1)
        time[i + 1] = time[i] + tSample
        sAcce0, sAcce1, sAcce2 = springCalcBeeman(springs, sForce, sAcce0, sAcce1, sAcce2, saveSteps, dt)
            
        for j in range(n):
            springs[j].vList[i + 1] = springs[j].v
            springs[j].xList[i + 1] = springs[j].x
        energy[i + 1] = energyCalc(springs)
        
    t1 = ti.time()
    print('Beeman time: ' + str(t1 - t0))
        
    return springs, energy, time

#%%

def springSimulRK4(Tmax, dt, tSample, sArray):
    """
    Função:
    ---------
    Executa a simulação segundo o algoritmo de Runge-Kutta de Ordem 4

    Parameters
    ----------
    Tmax : Float
        Tempo total da simulação
    dt : Float
        Tempo entre passos
    tSample : Float
        Tempo entre cada amostragem
    sArray : Array de strings
        Array com as características de inicialização de cada corpo indicadas pelo usuário na GUI.

    Returns
    -------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema
    energy : Array de floats
        Array com as energias do sistema a cada amostragem
    time : Array de floats
        Array com os tempos de cada amostragem
    """
    t0 = ti.time()
    size, saveSteps, n, springs, sForce, sAcce, time, energy = initSimul(Tmax, dt, tSample, sArray)
    
    for i in range(n):
        springs[i] = Body(sArray[i][0], sArray[i][1], sArray[i][2], sArray[i][3], sArray[i][4], size + 1)
    
    energy[0] = energyCalc(springs)
    
    for i in range(size):
        time[i + 1] = time[i] + tSample
        springCalcRK4(springs, sForce, sAcce, saveSteps, dt)
        
        for j in range(n):
            springs[j].vList[i + 1] = springs[j].v
            springs[j].xList[i + 1] = springs[j].x
        energy[i + 1] = energyCalc(springs)
        
    t1 = ti.time()
    print('RK4 time: ' + str(t1 - t0))
        
    return springs, energy, time

#%%

def initPlots(springs):
    """
    Função:
    ---------
    Inicia a figura e os plots utilizados para animação da simulação

    Parameters
    ----------
    springs : Array de objetos
        Array com as várias molas/corpos do sistema

    Returns
    -------
    plots : Array de plots
        Array com 2 plots para a animação: um para representação gráfica dos corpos, e outro das molas
    """
    size = springs.size # Indicador do número de corpos/molas
    plots = np.zeros((size, 2), dtype = object) # Cria 2 plots para cada corpo. Um com bolas vermelhas indicadoras de posição, outro com traços da mola
    
    for i in range(size):
        plots[i, 0], = plt.plot([], [], "o", color = "red", markersize = 20, zorder = 1) # Bolas vermelhas, na layer superior
        plots[i, 1], = plt.plot([], [], "-", color = "black", zorder = 0) # Traços pretos, na layer inferior
        
    return plots

#%%

def makeAnimation(i):
    """
    Função:
    ---------
    Função chamada pela função FuncAnimation, responsável pela animação da simulação

    Parameters
    ----------
    i : Objeto do array de frames
        Contém as posições de certa iteração para todos os corpos

    Returns
    -------
    Nada. Apenas trata de atualizar os dados durante a animação
    """
    s = i.size

    if s == 1:
        plotsAni[0, 0].set_data(i, 0) # Atualiza o valor da posição do corpo
        springsx = [] # Inicia o array de coordenadas X para cada vértice das molas
        springsy = [] # Inicia o array de coordenadas Y para cada vértice das molas
        nsprings = 20 # Indica quantos nodos cada mola terá
        for k in range(nsprings + 1):
            springsx.append(k * i/nsprings)
            springsy.append(0.2 * np.sin(k * np.pi/2)) # Usa-se o sin(k pi/2) de modo ao valor do Y alternar entre positivo e negativo
        plotsAni[0, 1].set_data(springsx, springsy) # Desenha a mola
        
    else: # Neste caso, a posição do nodo das molas deve ter em conta a posição do corpo anterior
        for j in range(i.size):
            plotsAni[j, 0].set_data(i[j], 0)
            springsx = []
            springsy = []
            nsprings = 20
            if j == 0 :
                for k in range(nsprings + 1):
                    springsx.append(k * i[j]/nsprings)
                    springsy.append(0.2 * np.sin(k * np.pi/2))
            else:
                for k in range(nsprings + 1):
                    springsx.append(i[j - 1] + k * (i[j] - i[j - 1])/nsprings)
                    springsy.append(0.2 * np.sin(k * np.pi/2))
            plotsAni[j, 1].set_data(springsx, springsy)
    
#%%

def runGui(*args):
    """
    Função:
    ---------
    Inicia as simulações com as características selecionadas após se premir o botão Run da GUI

    Parameters
    ----------
    *args : TYPE
        DESCRIPTION.

    Returns
    -------
    None.
    """
    global ani
    global plotsAni
    global springTextArray
    
    alg = algcb.get_status()
    
    tmax = float(tmaxtb.text) # Vai buscar o valor introduzido pelo utilizador
    dt = float(dttb.text) # Vai buscar o valor introduzido pelo utilizador
    tSample = float(tsamtb.text) # Vai buscar o valor introduzido pelo utilizador
    
    molas = []

    for i in range(len(springTextArray)): # Vai buscar o valor de cada característica do corpo/mola definido pelo utilizador
        s0 = float(springTextArray[i][1].text)
        s1 = float(springTextArray[i][3].text)
        s2 = float(springTextArray[i][5].text)
        s3 = float(springTextArray[i][7].text)
        s4 = float(springTextArray[i][9].text)
        S = [s0, s1, s2, s3, s4]
        molas.append(S) # Adiciona as características para mais tarde se criarem os objetos
    
    fig, ax = plt.subplots(figsize = (10, 6)) # Inicializa-se o plot das Posições
    ax.set_title('Posição de Cada Corpo')
    ax.set_xlabel('Tempo (s)')
    ax.set_ylabel('Posição (m)')
    
    fig2, ax2 = plt.subplots(figsize = (10, 6)) # Inicializa-se o plot das Frequências
    ax2.set_title('Transformadas de Fourier')
    ax2.set_xlabel('Frequência (Hz)')
    ax2.set_ylabel('Intensidade')
    
    fig3, ax3 = plt.subplots(figsize = (10, 6)) # Inicializa-se o plot das Energias
    ax3.set_title('Evolução da Energia do Sistema')
    ax3.set_xlabel('Tempo (s)')
    ax3.set_ylabel('Energia (J)')
    
    
    # Consoante os algorítmos escolhidos, o programa irá fazer os cálculos e gráficos.
    if alg[0] == True:  
        a, b, t = springSimulCromer(tmax, dt, tSample, molas)
        for i in range(a.size):
            ax.plot(t, a[i].xList, color = 'blue', label = 'Mola ' + str(i + 1) + ' - Euler-Cromer')
            fourier = sc.rfft(a[i].xList)
            fourierfreq = sc.rfftfreq(a[0].xList.size, tSample)
            ax2.plot(fourierfreq, abs(fourier), color = 'blue', label = 'Mola ' + str(i + 1) + ' - Euler-Cromer')
        ax3.plot(t, b, color = 'blue', label = 'Euler-Cromer')
        an = a
        nome = 'Animação: Método de Euler-Cromer'
        
    if alg[1] == True:
        a2, b2, t2 = springSimulVerlet(tmax, dt, tSample, molas)
        for i in range(a2.size):
            ax.plot(t2, a2[i].xList, color = 'darkorange', label = 'Mola ' + str(i + 1) + ' - Verlet')
            fourier2 = sc.rfft(a2[i].xList)
            fourierfreq = sc.rfftfreq(a2[0].xList.size, tSample)
            ax2.plot(fourierfreq, abs(fourier2), color = 'darkorange', label = 'Mola ' + str(i + 1) + ' - Verlet')
        ax3.plot(t2, b2, color = 'darkorange', label = 'Verlet')
        an = a2
        nome = 'Animação: Método de Verlet'
        
    if alg[2] == True:
        a3, b3, t3 = springSimulBeeman(tmax, dt, tSample, molas)
        for i in range(a3.size):
            ax.plot(t3, a3[i].xList, color = 'seagreen', label ='Mola ' + str(i + 1)+ ' - Beeman')
            fourier3 = sc.rfft(a3[i].xList)
            fourierfreq = sc.rfftfreq(a3[0].xList.size, tSample)
            ax2.plot(fourierfreq, abs(fourier3), color = 'seagreen', label = 'Mola ' + str(i + 1) + ' - Beeman')
        ax3.plot(t3, b3, color = 'seagreen', label = 'Beeman')
        an = a3
        nome = 'Animação: Método de Beeman'
            
    if alg[3] == True:
        a4, b4, t4 = springSimulRK4(tmax, dt, tSample, molas)
        for i in range(a4.size):
            ax.plot(t4, a4[i].xList, color = 'r', label = 'Mola ' + str(i + 1) + ' - RK4')
            fourier4 = sc.rfft(a4[i].xList)
            fourierfreq = sc.rfftfreq(a4[0].xList.size, tSample)
            ax2.plot(fourierfreq, abs(fourier4), color = 'r', label = 'Mola ' + str(i + 1) + ' - RK4')
        ax3.plot(t4, b4, color = 'r', label = 'RK4')
        an = a4
        nome = 'Animação: Runge-Kutta de Ordem 4'
            
    ax.legend()
    ax2.legend()
    ax3.legend()
    ax2.set_xlim([0.1, 2])
    ax2.set_ylim([0, 20000])
        
    #A animação começa a ser executada a partir desta linha
    if an.size == 1:
        r = an[0].xList
    else:
        for i in range(an.size - 1):
            if i == 0:
                r = np.column_stack((an[0].xList, an[1].xList))
            else:
                r = np.column_stack((r, an[i + 1].xList))
            
    figAni, axAni = plt.subplots(figsize = (10, 4))
    axAni.set_xlim(0, np.amax(r) * 1.1)
    axAni.set_ylim(-5, 5)
    axAni.set_xlabel('x (m)')
    axAni.get_yaxis().set_visible(False)
    plotsAni = initPlots(an)
    figAni.suptitle(nome, fontsize = 16)
    ani = animation.FuncAnimation(figAni, makeAnimation, frames = r, interval = .1)

#%%

def addSpring(*args): # Cria um novo espaço para o utilizador introduzir os dados da nova mola
    
    global pos
    global springTextArray    
    global molaName
    global xIn
    global butPos
    global plusax
    global minax
    
    molaName += 1
    xIn += 3
    pos -= 0.05 # Posição Y das novas caixas de texto
    butPos -= 0.05
    
    s0 = plt.axes([0.15, pos, 0.05, 0.03])
    s1 = TextBox(s0, 'Mola ' + str(molaName) + ': Massa(kg)', initial = '1')

    s2 = plt.axes([0.25, pos, 0.05, 0.03])
    s3 = TextBox(s2, '$k$(N/m)', initial = '10')

    s4 = plt.axes([0.35, pos, 0.05, 0.03])
    s5 = TextBox(s4, '$d_{Eq}$(m)', initial = '5')

    s6 = plt.axes([0.45, pos, 0.05, 0.03])
    s7 = TextBox(s6, '$x_0$(m)', initial = str(xIn))

    s8 = plt.axes([0.55, pos, 0.05, 0.03])
    s9 = TextBox(s8, '$v_0$(m/s)', initial = '0')
    
    sA0 = [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9]
    
    springTextArray.append(sA0)
    
    plusax.set_position([0.35, butPos, 0.03, 0.03], which = 'both') # altera a posição do botão de adicionar mola
    minax.set_position([0.25, butPos, 0.03, 0.03], which = 'both')  # altera a posição do botão de retirar mola
    
#%%    
    
def takeSpring(*args):

    global pos
    global xIn
    global butPos
    global springTextArray
    global molaName
    
    if molaName > 1 : # Apenas faz mudanças se existir mais que uma mola
        pos += 0.05
        butPos += 0.05
        molaName -= 1
        xIn -= 3
        
        for i in range(5):
            springTextArray[-1][i * 2].remove() # Apaga os plots de texto
            
        springTextArray.pop() # Apaga a posição no vetor

        plusax.set_position([0.35, butPos, 0.03, 0.03], which = 'both')
        minax.set_position([0.25, butPos, 0.03, 0.03], which = 'both')
    
#%%
    
def exitSim(*args):
    plt.close()
    
#%%

def fullScreen(*args):
    manager.full_screen_toggle()

#%%

butPos = 0.7
pos = 0.8
molaName = 1
xIn = 7

gui = plt.figure(figsize = (12, 7))

gui.suptitle('Simulação de Sistemas Massa-Mola', fontsize = '20')
gui.text(0.05, 0.9, 'Gonçalo&Grilo Inc.', fontsize = '20')

#Textboxes para os meta-parâmetros
dtax = plt.axes([0.85, 0.8, 0.05, 0.03])
dttb = TextBox(dtax, '$dt$(s)', initial = '0.001')

tmaxax = plt.axes([0.85, 0.7, 0.05, 0.03])
tmaxtb = TextBox(tmaxax, '$t_{Max}$(s)', initial = '100')

tsamax = plt.axes([0.85, 0.6, 0.05, 0.03])
tsamtb = TextBox(tsamax, '$t_{Sample}$(s)', initial = '0.01')

#Textboxes para as características do sistema
springTextArray = []

s0 = plt.axes([0.15, 0.8, 0.05, 0.03])
s1 = TextBox(s0, 'Mola ' + str(molaName) + ': Massa(kg)', initial = '1')

s2 = plt.axes([0.25, 0.8, 0.05, 0.03])
s3 = TextBox(s2, '$k$(N/m)', initial = '10')

s4 = plt.axes([0.35, 0.8, 0.05, 0.03])
s5 = TextBox(s4, '$d_{Eq}$(m)', initial = '5')

s6 = plt.axes([0.45, 0.8, 0.05, 0.03])
s7 = TextBox(s6, '$x_0$(m)', initial = str(xIn))

s8 = plt.axes([0.55, 0.8, 0.05, 0.03])
s9 = TextBox(s8, '$v_0$(m/s)', initial = '0')

sA0 = [s0, s1, s2, s3, s4, s5, s6, s7, s8, s9]

springTextArray.append(sA0)

#Checkboxes
algax = plt.axes([0.65, 0.65, 0.12, 0.2])
algcb = CheckButtons(algax, ['Euler-Cromer', 'Verlet', 'Beeman', 'RK4'])

#Botões
runax = plt.axes([0.70, 0.3, 0.2, 0.2])
runbut = Button(runax, 'Run')
runbut.on_clicked(runGui)

plusax = plt.axes([0.35, butPos, 0.03, 0.03])
plusbut = Button(plusax, '+')
plusbut.on_clicked(addSpring)

minax = plt.axes([0.25, butPos, 0.03, 0.03])
minbut = Button(minax, '-')
minbut.on_clicked(takeSpring)

fScreenax = plt.axes([0.70, 0.2, 0.08, 0.05])
FSbut = Button(fScreenax,'Full Screen')
FSbut.on_clicked(fullScreen)

closeax = plt.axes([0.82, 0.2, 0.08, 0.05])
closebut = Button(closeax, 'Exit')
closebut.on_clicked(exitSim)

manager = plt.get_current_fig_manager()
