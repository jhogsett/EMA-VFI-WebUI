"""EMA-VFI Engine Encapsulation Class"""
import sys

'''==========import from our code=========='''
sys.path.append('.')
import config as cfg # pylint: disable=import-error
from Trainer import Model # pylint: disable=import-error

class InterpolateEngine:
    """Singleton class encapsulating the EMA-VFI engine and related logic"""
    # model should be "ours" or "ours_small", or your own trained model
    # gpu_ids is for *future use*
    # if use_time_step is True "_t" is appended to the model name
    def __new__(cls, model : str, gpu_ids : str, use_time_step : bool=False):
        if not hasattr(cls, 'instance'):
            cls.instance = super(InterpolateEngine, cls).__new__(cls)
            cls.instance.init(model, gpu_ids, use_time_step)
        elif cls.instance.model_name != model or cls.instance.use_time_step != use_time_step:
            cls.instance = super(InterpolateEngine, cls).__new__(cls)
            cls.instance.init(model, gpu_ids, use_time_step)
        return cls.instance

    def init(self, model : str, gpu_ids: str, use_time_step):
        """Iniitalize the class by calling into EMA-VFI code"""
        gpu_id_array = self.init_device(gpu_ids)
        self.model_name = model
        self.use_time_step = use_time_step
        self.model = self.init_model(model, gpu_id_array, use_time_step)

    def init_device(self, gpu_ids : str):
        """for *future use*"""
        str_ids = gpu_ids.split(',')
        gpu_ids = []
        for str_id in str_ids:
            _id = int(str_id)
            if _id >= 0:
                gpu_ids.append(_id)
        # for *future use*
        # if len(gpu_ids) > 0:
        #     torch.cuda.set_device(gpu_ids[0])
        # cudnn.benchmark = True
        return gpu_ids

    def init_model(self, model, gpu_id_array, use_time_step):
        """EMA-VFI code from demo_2x.py"""
        # for *future use*
        # device = torch.device('cuda' if len(gpu_id_array) != 0 else 'cpu')
        '''==========Model setting=========='''
        TTA = True
        if model == 'ours_small':
            TTA = False
            cfg.MODEL_CONFIG['LOGNAME'] = 'ours_small' + ("_t" if use_time_step else "")
            cfg.MODEL_CONFIG['MODEL_ARCH'] = cfg.init_model_config(
                F = 16,
                depth = [2, 2, 2, 2, 2]
            )
        else:
            cfg.MODEL_CONFIG['LOGNAME'] = 'ours' + ("_t" if use_time_step else "")
            cfg.MODEL_CONFIG['MODEL_ARCH'] = cfg.init_model_config(
                F = 32,
                depth = [2, 2, 2, 4, 4]
            )
        model = Model(-1)
        model.load_model()
        model.eval()
        model.device()
        return {"model" : model, "TTA" : TTA}
