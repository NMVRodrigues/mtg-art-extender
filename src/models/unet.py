import torch
import torch.nn as nn
import torch.nn.functional as F


class UNet(nn.Module):
    def __init__(self, n_chanels):
        super(UNet, self).__init__()

        self.encoder = Encoder(n_chanels)
        self.decoder = Decoder(n_chanels)

    def forward(self,x):
        pass




class Encoder(nn.Module):
    def __init__(self, n_chanels):
        super(Encoder, self).__init__()

        self.act = nn.LeakyReLU(negative_slope=0.2)
        self.norm = nn.BatchNorm2d()


        # isto da para fazer com um ModuleList que deixa iterar sobre as layers, mas inicialmente pode ficar assim
        self.initial_conv = nn.Conv2d(n_chanels, 64, kernel_size=4, stride=2)
        self.c1 = nn.Conv2d(64, 128, kernel_size=4, stride=2)
        self.c2 = nn.Conv2d(128, 256, kernel_size=4, stride=2)
        self.c3 = nn.Conv2d(256, 512, kernel_size=4, stride=2)
        self.c4 = nn.Conv2d(512, 512, kernel_size=4, stride=2)
        self.c5 = nn.Conv2d(512, 512, kernel_size=4, stride=2)
        self.c6 = nn.Conv2d(512, 512, kernel_size=4, stride=2)
        self.c7 = nn.Conv2d(512, 512, kernel_size=4, stride=2)


    def forward(self, x):
        x = self.initial_conv(x)
        x1 = self.norm(self.c1(self.act(x)))
        x2 = self.norm(self.c2(self.act(x1)))
        x3 = self.norm(self.c3(self.act(x2)))
        x4 = self.norm(self.c4(self.act(x3)))
        x5 = self.norm(self.c5(self.act(x4)))
        x6 = self.norm(self.c6(self.act(x5)))
        x7 = self.norm(self.c7(self.act(x6)))

        return x7
    


class Decoder(nn.Module):
    def __init__(self, n_chanels):
        super(Decoder, self).__init__()

        self.act = nn.ReLU(negative_slope=0.2)
        self.norm = nn.BatchNorm2d()
        self.drop = nn.Dropout2d(p=0.5)
